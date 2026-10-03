"""Who plays what, and where the game runs.

HostSession runs the game: single player (no server) or hosting a network game (a lobby first). Remote players
send their actions; the host applies them, then sends everyone the events and the new state. ClientSession joins
a host and mirrors its state. Both look the same to the UI: `game` (the state), `my_seat`, `act(action)`,
`chat(text)`, `poll()` (call every frame: returns new events for the scene), `log`, `phase` ("lobby", "game").
"""
import random
import time

from . import bots
from .net import DEFAULT_PORT, Client, Server, local_ip
from .rules import Game, IllegalMove, apply

MAX_NAME = 16
BOT_NAMES = ["Sir Aldric", "Brother Hode", "Dame Isolde", "Old Tam", "Wynn the Bow", "Garrick", "Mother Ebba",
             "Fennick", "Black Rowan", "Ulfgar"]
PROTOCOL = 1


def clean(text, limit):
    return "".join(c for c in str(text) if c.isprintable())[:limit].strip()


class SessionBase:
    def __init__(self):
        self.game = None
        self.my_seat = None
        self.seats = []  # [{"name", "kind": "human"|"bot"|"remote", "cid"}]
        self.log = []  # (text, kind) kind: "chat", "system", "game"
        self.phase = "lobby"
        self.error = None
        self.bot_delay = 0.7  # seconds between a bot's moves
        self.is_host = False
        self.networked = False

    def say(self, text, kind="system"):
        self.log.append((text, kind))
        del self.log[:-300]

    @property
    def names(self):
        return [s["name"] for s in self.seats]


class HostSession(SessionBase):
    def __init__(self, name, max_players=4, bots_on=True, port=None, seed=None):
        super().__init__()
        self.is_host = True
        self.rng = random.Random(seed)
        self.seed = seed
        self.server = Server(port) if port is not None else None
        self.networked = self.server is not None
        self.max_players = max_players
        self.bots_on = bots_on
        self.seats = [{"name": clean(name, MAX_NAME) or "Player", "kind": "human", "cid": None}]
        self.my_seat = 0
        self._bot_wait = 0.0
        self._offered = {}
        self.scene_busy = lambda: False  # the UI sets this, so bots wait for animations
        if self.server:
            self.say(f"Hosting on {local_ip()}:{self.server.port}. Waiting for players...")

    @property
    def port(self):
        return self.server.port if self.server else None

    # ---------------------------------------------------------------------------------------------- lobby

    def set_max_players(self, n):
        humans = sum(1 for s in self.seats if s["kind"] != "bot")
        self.max_players = max(1, min(6, max(n, humans)))
        while len(self.seats) > self.max_players:
            bot = next((i for i in range(len(self.seats) - 1, -1, -1) if self.seats[i]["kind"] == "bot"), None)
            if bot is None:
                break
            self.seats.pop(bot)
        self._publish_lobby()

    def set_bots(self, on):
        self.bots_on = on
        self._publish_lobby()

    def fill_bots(self):
        used = {s["name"] for s in self.seats}
        names = [n for n in BOT_NAMES if n not in used]
        self.rng.shuffle(names)
        while len(self.seats) < self.max_players and names:
            self.seats.append({"name": names.pop(), "kind": "bot", "cid": None})

    def start(self):
        if self.bots_on:
            self.fill_bots()
        self.game = Game(self.names, seed=self.seed if self.seed is not None else self.rng.randrange(1 << 30))
        self.phase = "game"
        self.say(f"The siege begins! {len(self.seats)} defender{'s' if len(self.seats) > 1 else ''}.")
        events = self.game.take_events()
        if self.server:
            for i, s in enumerate(self.seats):
                if s["kind"] == "remote":
                    self.server.send(s["cid"], {"t": "start", "seat": i, "seats": self.seats,
                                                "state": self.game.to_dict()})
        return events

    def restart(self):
        self.seats = [s for s in self.seats if s["kind"] != "bot"]
        return self.start()

    def _publish_lobby(self):
        if self.server:
            self.server.broadcast({"t": "lobby", "seats": self.seats, "max": self.max_players, "bots": self.bots_on})

    # ---------------------------------------------------------------------------------------------- playing

    def act(self, action, seat=None):
        """Apply an action for a seat (default: mine). Returns the new events, or raises IllegalMove."""
        seat = self.my_seat if seat is None else seat
        apply(self.game, seat, action)
        events = self.game.take_events()
        self._broadcast_events(events)
        return events

    def _broadcast_events(self, events):
        if self.server and events:
            self.server.broadcast({"t": "events", "events": events, "state": self.game.to_dict()})

    def chat(self, text):
        text = clean(text, 200)
        if not text:
            return
        name = self.seats[self.my_seat]["name"]
        self.say(f"{name}: {text}", "chat")
        if self.server:
            self.server.broadcast({"t": "chat", "name": name, "text": text})

    def poll(self, dt=0.0):
        """Network messages and bot moves; returns new game events for the scene."""
        events = []
        if self.server:
            events += self._poll_network()
        if self.phase == "game" and self.game and self.game.phase != "over":
            events += self._bots(dt)
        return events

    def _bot_seats(self):
        g = self.game
        if g.pending:
            return [s for s in g.pending if self.seats[s]["kind"] == "bot"]
        if g.trade_offer:
            s = g.trade_offer["to"]
            return [s] if self.seats[s]["kind"] == "bot" else []
        return [g.current] if self.seats[g.current]["kind"] == "bot" else []

    def _bots(self, dt):
        self._bot_wait -= dt
        if self._bot_wait > 0 or self.scene_busy():
            return []
        for seat in self._bot_seats():
            key = (self.game.turn, seat)
            offered = self._offered.setdefault(key, set())
            action = bots.next_action(self.game, seat, offered)
            if action is None:
                continue
            try:
                ev = self.act(action, seat)
            except IllegalMove as e:  # a bot bug must never hang the game
                self.say(f"({self.seats[seat]['name']} fumbles: {e})")
                ev = self.act({"a": "end"}, seat) if self.game.current == seat and not self.game.pending else []
            self._bot_wait = self.bot_delay
            return ev
        return []

    def _poll_network(self):
        events = []
        while True:
            try:
                kind, cid, msg = self.server.inbox.get_nowait()
            except Exception:
                break
            if kind == "connect":
                continue
            if kind == "disconnect":
                events += self._disconnect(cid)
                continue
            events += self._handle(cid, msg) or []
        return events

    def _seat_of(self, cid):
        return next((i for i, s in enumerate(self.seats) if s["cid"] == cid), None)

    def _handle(self, cid, msg):
        t = msg.get("t")
        if t == "hello":
            if self.phase != "lobby":
                return self._refuse(cid, "The game has already begun.")
            if len(self.seats) >= self.max_players:
                return self._refuse(cid, "The game is full.")
            name = clean(msg.get("name", ""), MAX_NAME) or "Player"
            used = {s["name"] for s in self.seats}
            base, n = name, 2
            while name in used:
                name = f"{base[:MAX_NAME - 2]}{n}"
                n += 1
            self.seats.append({"name": name, "kind": "remote", "cid": cid})
            self.server.send(cid, {"t": "welcome", "name": name, "protocol": PROTOCOL})
            self.say(f"{name} joins.")
            self.server.broadcast({"t": "chat", "name": None, "text": f"{name} joins."})
            self._publish_lobby()
            return []
        seat = self._seat_of(cid)
        if seat is None:
            return []
        if t == "chat":
            text = clean(msg.get("text", ""), 200)
            if text:
                name = self.seats[seat]["name"]
                self.say(f"{name}: {text}", "chat")
                self.server.broadcast({"t": "chat", "name": name, "text": text})
            return []
        if t == "act" and self.phase == "game":
            try:
                return self.act(msg.get("action") or {}, seat)
            except (IllegalMove, KeyError, TypeError, ValueError) as e:
                self.server.send(cid, {"t": "error", "msg": str(e)})
        return []

    def _refuse(self, cid, reason):
        self.server.send(cid, {"t": "refused", "msg": reason})
        self.server.drop(cid)
        return []

    def _disconnect(self, cid):
        seat = self._seat_of(cid)
        self.server.drop(cid)
        if seat is None:
            return []
        name = self.seats[seat]["name"]
        if self.phase == "lobby":
            self.seats.pop(seat)
            self.say(f"{name} leaves.")
            self._publish_lobby()
            return []
        self.seats[seat]["kind"] = "bot"
        self.seats[seat]["cid"] = None
        self.say(f"{name} leaves; a bot takes over their defence.")
        self.server.broadcast({"t": "chat", "name": None, "text": f"{name} left; a bot takes over."})
        return []

    def close(self):
        if self.server:
            self.server.close()


def single_player(name, players=1, seed=None):
    """1 player is the solo game; more are filled with bots."""
    s = HostSession(name, max_players=players, bots_on=True, port=None, seed=seed)
    return s


class ClientSession(SessionBase):
    def __init__(self, name, host, port=DEFAULT_PORT):
        super().__init__()
        self.networked = True
        self.client = Client(host, port)
        self.client.send({"t": "hello", "name": clean(name, MAX_NAME), "protocol": PROTOCOL})
        self.max_players = 0
        self.bots_on = True
        self.say(f"Connected to {host}:{port}.")

    def act(self, action):
        self.client.send({"t": "act", "action": action})
        return []

    def chat(self, text):
        text = clean(text, 200)
        if text:
            self.client.send({"t": "chat", "text": text})

    def poll(self, dt=0.0):
        events = []
        while True:
            try:
                kind, _, msg = self.client.inbox.get_nowait()
            except Exception:
                break
            if kind == "disconnect":
                self.error = "Lost the connection to the host."
                self.say(self.error)
                continue
            t = msg.get("t")
            if t == "welcome":
                self.say(f"Joined as {msg['name']}.")
                self.my_name = msg["name"]
            elif t == "refused":
                self.error = msg.get("msg", "Refused.")
                self.say(self.error)
            elif t == "lobby":
                self.seats, self.max_players, self.bots_on = msg["seats"], msg["max"], msg["bots"]
            elif t == "start":
                self.seats = msg["seats"]
                self.my_seat = msg["seat"]
                self.game = Game.from_dict(msg["state"])
                self.phase = "game"
                self.say("The siege begins!")
                events.append({"e": "_sync"})
            elif t == "events":
                old = self.game
                self.game = Game.from_dict(msg["state"])
                if old is not None and hasattr(old, "_kinds"):
                    self.game._kinds = old._kinds
                events += msg["events"]
            elif t == "chat":
                self.say(f"{msg['name']}: {msg['text']}" if msg.get("name") else msg["text"],
                         "chat" if msg.get("name") else "system")
            elif t == "error":
                self.say(f"(host: {msg.get('msg')})")
        return events

    def close(self):
        self.client.close()
