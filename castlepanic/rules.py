"""Castle Panic rules: the whole game state and every move, with no graphics, sound or networking.

The board is six arcs (0..5, printed 1..6, numbered clockwise) by five rings: CASTLE (0, the Towers), SWORDSMAN,
KNIGHT, ARCHER and FOREST (4, where Monsters arrive). Arcs 0-1 are red, 2-3 green, 4-5 blue. A Wall stands on the
line between each arc's Swordsman ring and its Castle space.

A turn goes through six steps (`STEPS`, `game.phase`): draw up (done for the player, straight on to step 2),
discard and draw 1 (two in solo), trade 1 card (in a 6-player game 2, with two different players), play cards, the
Monsters move, 2 new Monsters are drawn; the player moves on from each with `next_step`; then the next player
draws up. All hands are open: this is a
co-operative game.

`Game` holds the state as plain data (`to_dict`/`from_dict` round-trip it through JSON, which is how the host sends
it to clients). Each move (`discard`, `trade`, `play`, `next_step`, ...) checks it is legal, raises
`IllegalMove` if not, and appends `Event`s to `game.events`: what happened, in order, for the scene to animate and
the log to tell. Randomness comes from `game.rng`, seeded, so a game replays exactly.
"""
import random

ARCS = 6
CASTLE, SWORDSMAN, KNIGHT, ARCHER, FOREST = range(5)
RING_NAMES = ["Castle", "Swordsman", "Knight", "Archer", "Forest"]
COLORS = ["red", "green", "blue"]
HIT_RING = {"swordsman": SWORDSMAN, "knight": KNIGHT, "archer": ARCHER}


def arc_color(arc):
    return COLORS[arc // 2]


def arcs_of(color):
    i = COLORS.index(color)
    return (2 * i, 2 * i + 1)


# ------------------------------------------------------------------------------------------------ the pieces

# Castle deck, 49 cards: (kind, color, count)
DECK = [
    *[(k, c, 3) for k in ("archer", "knight", "swordsman") for c in COLORS],
    *[(k, "any", 1) for k in ("archer", "knight", "swordsman")],
    *[("hero", c, 1) for c in COLORS],
    ("brick", None, 4), ("mortar", None, 4),
    ("barbarian", None, 1), ("nice_shot", None, 1), ("tar", None, 1), ("fortify", None, 1),
    ("drive_back", None, 1), ("missing", None, 1), ("draw2", None, 1), ("scavenge", None, 1),
]

CARD_TITLES = {
    "archer": "Archer", "knight": "Knight", "swordsman": "Swordsman", "hero": "Hero", "brick": "Brick",
    "mortar": "Mortar", "barbarian": "Barbarian", "nice_shot": "Nice Shot", "tar": "Tar",
    "fortify": "Fortify Wall", "drive_back": "Drive Him Back!", "missing": "Missing", "draw2": "Draw 2 Cards",
    "scavenge": "Scavenge",
}

CARD_HELP = {
    "archer": "Hit 1 Monster in the Archer ring",
    "knight": "Hit 1 Monster in the Knight ring",
    "swordsman": "Hit 1 Monster in the Swordsman ring",
    "hero": "Hit 1 Monster in the Archer, Knight or Swordsman ring",
    "brick": "Play with Mortar to rebuild a Wall",
    "mortar": "Play with Brick to rebuild a Wall",
    "barbarian": "Slay 1 Monster anywhere but the Forest (Castle too)",
    "nice_shot": "Play with a hit card: that Monster is slain",
    "tar": "1 Monster doesn't move this turn (anywhere, Castle too)",
    "fortify": "Fortify 1 Wall: it survives the next attack",
    "drive_back": "Send 1 Monster back to the Forest (Castle too)",
    "missing": "Draw no Monsters this turn",
    "draw2": "Draw 2 more cards",
    "scavenge": "Take any 1 card from the discard pile",
}

# Monster pile, 49 tokens: (kind, count). Damage points and victory points per Monster kind.
TOKENS = [
    ("goblin", 6), ("orc", 11), ("troll", 10),
    ("goblin_king", 1), ("orc_warlord", 1), ("troll_mage", 1), ("healer", 1),
    ("boulder", 4),
    ("move_red", 2), ("move_green", 2), ("move_blue", 2), ("move_cw", 1), ("move_ccw", 1),
    ("plague_archer", 1), ("plague_knight", 1), ("plague_swordsman", 1),
    ("discard1", 1), ("draw3", 1), ("draw4", 1),
]
HP = {"goblin": 1, "orc": 2, "troll": 3, "goblin_king": 2, "orc_warlord": 3, "troll_mage": 3, "healer": 2}
POINTS = {"goblin": 1, "orc": 2, "troll": 3, "goblin_king": 4, "orc_warlord": 4, "troll_mage": 4, "healer": 4}
BOSSES = ("goblin_king", "orc_warlord", "troll_mage", "healer")

TOKEN_TITLES = {
    "goblin": "Goblin", "orc": "Orc", "troll": "Troll", "goblin_king": "Goblin King", "orc_warlord": "Orc Warlord",
    "troll_mage": "Troll Mage", "healer": "Healer", "boulder": "Giant Boulder", "move_red": "Red Monsters Move 1",
    "move_green": "Green Monsters Move 1", "move_blue": "Blue Monsters Move 1", "move_cw": "Monsters Move Clockwise",
    "move_ccw": "Monsters Move Counter-clockwise", "plague_archer": "Plague! Archers",
    "plague_knight": "Plague! Knights", "plague_swordsman": "Plague! Swordsmen",
    "discard1": "All Players Discard 1 Card", "draw3": "Draw 3 Monster Tokens", "draw4": "Draw 4 Monster Tokens",
}


def hand_size(players):
    return {1: 6, 2: 6, 6: 4}.get(players, 5)


def trades_allowed(players):
    return 0 if players == 1 else 2 if players == 6 else 1


def card_title(card):
    t = CARD_TITLES[card["kind"]]
    c = card["color"]
    if c == "any":
        return f"Any Color {t}"
    if c:
        return f"{c.capitalize()} {t}"
    return t


class IllegalMove(Exception):
    pass


def Event(_e, **data):
    """What just happened, for the scene to animate and the log to tell: a dict with "e" naming it."""
    return {"e": _e, **data}


# ------------------------------------------------------------------------------------------------ the game

# the steps of a turn, in order (game.phase); "over" once the game has ended
STEPS = ("draw_up", "discard", "trade", "play", "move", "draw_monsters")
STEP_TITLES = {"draw_up": "Draw Up", "discard": "Discard & Draw 1", "trade": "Trade", "play": "Play Cards",
               "move": "Monsters Move", "draw_monsters": "Draw 2 Monsters", "over": "Game Over"}


class Game:
    def __init__(self, names, seed=None):
        """names: one per seat, in turn order."""
        self.rng = random.Random(seed)
        self.names = list(names)
        n = len(self.names)
        self.hand_size = hand_size(n)
        self.max_discards = 2 if n == 1 else 1
        self.max_trades = trades_allowed(n)
        cards = []
        for kind, color, count in DECK:
            cards += [{"kind": kind, "color": color} for _ in range(count)]
        for i, c in enumerate(cards):
            c["id"] = i
        self.cards = {c["id"]: c for c in cards}
        self.deck = [c["id"] for c in cards]
        self.rng.shuffle(self.deck)
        self.discard_pile = []
        tokens = [k for k, count in TOKENS for _ in range(count)]
        self.monsters = {}  # id -> monster dict, those on the board
        self.next_mid = 1
        self.walls = [True] * ARCS
        self.fortified = [False] * ARCS
        self.towers = [True] * ARCS
        self.hands = [[] for _ in range(n)]
        self.trophies = [[] for _ in range(n)]  # kinds slain, per player
        self.monster_discard = []
        self.events = []
        self.turn = 0  # how many turns have begun
        self.current = 0
        self.phase = "draw_up"
        self.discards_used = 0
        self.trades_used = 0
        self.traded_with = []  # seats traded with this turn (a 6-player game's two trades are with two players)
        self.no_monsters = False  # Missing played this turn
        self.to_draw = 0  # monster tokens still to draw this turn
        self.pending = {}  # seat -> what that player must decide before play goes on ("discard1")
        self.trade_offer = None  # {"from", "to", "give", "take"} awaiting the other player
        self.result = None  # "won" or "lost" once over
        # setup: 3 Goblins, 2 Orcs and a Troll, one in each arc of the Archer ring
        starters = ["goblin"] * 3 + ["orc"] * 2 + ["troll"]
        for k in starters:
            tokens.remove(k)
        self.rng.shuffle(starters)
        self.rng.shuffle(tokens)
        self.pile = tokens
        for arc, kind in enumerate(starters):
            self._spawn(kind, arc, ARCHER)
        for seat in range(n):
            for _ in range(self.hand_size):
                self._draw_card(seat, quiet=True)
        self.events.append(Event("setup"))
        self._begin_turn(first=True)

    # -------------------------------------------------------------------------------- state as data

    FIELDS = ("names", "hand_size", "max_discards", "max_trades", "cards", "deck", "discard_pile", "monsters",
              "next_mid", "walls", "fortified", "towers", "hands", "trophies", "monster_discard", "turn", "current",
              "phase", "discards_used", "trades_used", "traded_with", "no_monsters", "to_draw", "pending", "trade_offer", "result",
              "pile")

    def to_dict(self, hide_pile=True):
        d = {f: getattr(self, f) for f in self.FIELDS}
        d["cards"] = list(self.cards.values())
        d["monsters"] = list(self.monsters.values())
        d["pending"] = {str(k): v for k, v in self.pending.items()}
        if hide_pile:
            d["pile"] = len(self.pile)
            d["deck"] = len(self.deck)
        return d

    @classmethod
    def from_dict(cls, d):
        g = cls.__new__(cls)
        g.rng = random.Random()
        for f in cls.FIELDS:
            setattr(g, f, d[f])
        g.cards = {c["id"]: c for c in d["cards"]}
        g.monsters = {m["id"]: m for m in d["monsters"]}
        g.pending = {int(k): v for k, v in d["pending"].items()}
        if isinstance(g.pile, int):
            g.pile = [None] * g.pile
        if isinstance(g.deck, int):
            g.deck = [None] * g.deck
        g.events = []
        return g

    # -------------------------------------------------------------------------------- queries

    @property
    def players(self):
        return len(self.names)

    def card(self, cid):
        return self.cards[cid]

    def hand(self, seat):
        return [self.cards[c] for c in self.hands[seat]]

    def monsters_at(self, arc, ring):
        return [m for m in self.monsters.values() if m["arc"] == arc and m["ring"] == ring]

    def score(self, seat):
        return sum(POINTS[k] for k in self.trophies[seat])

    def towers_left(self):
        return sum(self.towers)

    def can_hit(self, card, m):
        """Whether a hit card (archer, knight, swordsman, hero) can hit Monster m where it stands."""
        kind, color = card["kind"], card["color"]
        if m["ring"] in (CASTLE, FOREST):
            return False
        if kind == "hero":
            return arc_color(m["arc"]) == color
        if kind in HIT_RING:
            return m["ring"] == HIT_RING[kind] and (color == "any" or arc_color(m["arc"]) == color)
        return False

    def targets(self, cid):
        """The Monsters (ids) a card can be played on now, or None if it takes no Monster."""
        kind = self.cards[cid]["kind"]
        ms = list(self.monsters.values())
        if kind in ("archer", "knight", "swordsman", "hero"):
            return [m["id"] for m in ms if self.can_hit(self.cards[cid], m)]
        if kind == "barbarian":
            return [m["id"] for m in ms if m["ring"] != FOREST]
        if kind == "drive_back":
            return [m["id"] for m in ms if m["ring"] != FOREST]
        if kind == "tar":
            return [m["id"] for m in ms if not m["tar"]]
        return None

    def playable(self, seat, cid):
        """Whether the card can be played on its own now (Brick, Mortar and Nice Shot go in pairs)."""
        if seat != self.current or self.phase != "play" or self.pending or self.trade_offer:
            return False
        kind = self.cards[cid]["kind"]
        if kind in ("brick", "mortar"):
            other = "mortar" if kind == "brick" else "brick"
            return not all(self.walls) and any(self.cards[c]["kind"] == other for c in self.hands[seat])
        if kind == "nice_shot":
            return any(self.targets(c) for c in self.hands[seat] if self.cards[c]["kind"] in
                       ("archer", "knight", "swordsman", "hero"))
        if kind == "fortify":
            return any(w and not f for w, f in zip(self.walls, self.fortified))
        if kind == "scavenge":
            return bool(self.discard_pile)
        if kind == "missing":
            return not self.no_monsters
        if kind == "draw2":
            return True
        t = self.targets(cid)
        return bool(t)

    # -------------------------------------------------------------------------------- turn structure

    def _check(self, seat, phase=None):
        if self.phase == "over":
            raise IllegalMove("the game is over")
        if self.pending:
            raise IllegalMove("waiting for players to discard")
        if self.trade_offer:
            raise IllegalMove("waiting for an answer to a trade")
        if seat != self.current:
            raise IllegalMove("not your turn")
        if phase and self.phase not in phase:
            raise IllegalMove(f"not in the {'/'.join(phase)} phase")

    def _begin_turn(self, first=False):
        self.turn += 1
        self.discards_used = self.trades_used = 0
        self.traded_with = []
        self.no_monsters = False
        for m in self.monsters.values():  # Tar wears off at the start of the next player's turn
            if m["tar"]:
                m["tar"] = False
                self.events.append(Event("untar", mid=m["id"]))
        self.phase = "draw_up"
        self.events.append(Event("turn", seat=self.current, turn=self.turn))
        if not first:  # (the first player's hand was just dealt)
            drawn = self._fill_hand(self.current)
            self.events.append(Event("draw_up", seat=self.current, cards=drawn))
        self.phase = "discard"  # nothing to decide in Draw Up: straight on to step 2
        self.events.append(Event("step", seat=self.current, step=self.phase))

    def _fill_hand(self, seat):
        """Draw up to the hand size; returns the cards drawn."""
        drawn = []
        while len(self.hands[seat]) < self.hand_size:
            cid = self._draw_card(seat)
            if cid is None:  # (card 0 is a card too)
                break
            drawn.append(cid)
        return drawn

    def _draw_card(self, seat, quiet=False):
        if not self.deck:
            if not self.discard_pile:
                return None
            self.deck, self.discard_pile = self.discard_pile, []
            self.rng.shuffle(self.deck)
            self.events.append(Event("reshuffle"))
        cid = self.deck.pop()
        self.hands[seat].append(cid)
        if not quiet:
            self.events.append(Event("draw", seat=seat, card=cid))
        return cid

    def _discard(self, seat, cid, why="discard"):
        self.hands[seat].remove(cid)
        self.discard_pile.append(cid)
        self.events.append(Event("discard", seat=seat, card=cid, why=why))

    def discard(self, seat, cid):
        """Step 2: throw one card away (two in a solo game) and draw a replacement."""
        self._check(seat, ("discard",))
        if cid not in self.hands[seat]:
            raise IllegalMove("not in your hand")
        if self.discards_used >= self.max_discards:
            raise IllegalMove("no more discards this turn")
        self.discards_used += 1
        self._discard(seat, cid)
        self._draw_card(seat)

    def next_step(self, seat):
        """On to the next step of the turn. From Play the Monsters move; from Monsters Move 2 new Monsters are drawn,
        and then the next player's turn begins (Draw Up, which moves on to Discard by itself)."""
        self._check(seat)
        if self.phase in ("draw_up", "discard", "trade"):
            self.phase = {"draw_up": "discard", "discard": "trade" if self.max_trades else "play",
                          "trade": "play"}[self.phase]
            self.events.append(Event("step", seat=seat, step=self.phase))
        elif self.phase == "play":
            self._monsters_move()
        elif self.phase == "move":
            self._draw_monsters()
        else:
            raise IllegalMove("wait for the Monsters")

    def offer_trade(self, seat, to, give, take):
        """Step 3: offer one of your cards for one of theirs; `to` accepts or declines (answer_trade)."""
        self._check(seat, ("trade",))
        if self.trades_used >= self.max_trades:
            raise IllegalMove("no more trades this turn")
        if to == seat or not 0 <= to < self.players:
            raise IllegalMove("trade with someone else")
        if to in self.traded_with:
            raise IllegalMove(f"you've traded with {self.names[to]} already: the second trade is with someone else")
        if give not in self.hands[seat] or take not in self.hands[to]:
            raise IllegalMove("those cards aren't there")
        self.trade_offer = {"from": seat, "to": to, "give": give, "take": take}
        self.events.append(Event("offer", **self.trade_offer))

    def answer_trade(self, seat, accept):
        offer = self.trade_offer
        if not offer or seat != offer["to"]:
            raise IllegalMove("no trade offered to you")
        self.trade_offer = None
        a, b = offer["from"], offer["to"]
        if accept and offer["give"] in self.hands[a] and offer["take"] in self.hands[b]:
            self.hands[a].remove(offer["give"])
            self.hands[b].remove(offer["take"])
            self.hands[a].append(offer["take"])
            self.hands[b].append(offer["give"])
            self.trades_used += 1
            self.traded_with.append(b)
            self.events.append(Event("trade", **offer))
        else:
            self.events.append(Event("declined", **offer))

    def cancel_trade(self, seat):
        if self.trade_offer and self.trade_offer["from"] == seat:
            self.trade_offer = None
            self.events.append(Event("cancelled", seat=seat))

    # -------------------------------------------------------------------------------- playing cards

    def play(self, seat, cid, target=None, extra=None):
        """Step 4: play a card. target: a Monster id (hit cards, Barbarian, Tar, Drive Him Back!), a wall's arc
        (Fortify, or Brick/Mortar with the other as `extra`), a discard-pile card id (Scavenge). Nice Shot is
        played with its hit card as `extra`."""
        self._check(seat, ("play",))
        if cid not in self.hands[seat]:
            raise IllegalMove("not in your hand")
        card = self.cards[cid]
        kind = card["kind"]
        if kind in ("brick", "mortar"):
            return self._build(seat, cid, extra, target)
        if kind == "nice_shot":
            if extra not in self.hands[seat] or self.cards[extra]["kind"] not in HIT_RING and \
                    self.cards[extra]["kind"] != "hero":
                raise IllegalMove("Nice Shot goes with a hit card")
            m = self.monsters.get(target)
            if not m or not self.can_hit(self.cards[extra], m):
                raise IllegalMove("that card can't hit that Monster")
            self._discard(seat, cid, why="play")
            self._discard(seat, extra, why="play")
            self.events.append(Event("attack", seat=seat, card=extra, kind=self.cards[extra]["kind"], mid=target, nice=True))
            self._damage(m, m["hp"], by=seat, cause="nice_shot")
            return self._after_play()
        if kind in ("archer", "knight", "swordsman", "hero"):
            m = self.monsters.get(target)
            if not m or not self.can_hit(card, m):
                raise IllegalMove("that card can't hit that Monster")
            self._discard(seat, cid, why="play")
            self.events.append(Event("attack", seat=seat, card=cid, kind=kind, mid=target))
            self._damage(m, 1, by=seat, cause=kind)
            return self._after_play()
        if kind == "barbarian":
            m = self.monsters.get(target)
            if not m or m["ring"] == FOREST:
                raise IllegalMove("the Barbarian can't reach that")
            self._discard(seat, cid, why="play")
            self.events.append(Event("attack", seat=seat, card=cid, kind="barbarian", mid=target))
            self._damage(m, m["hp"], by=seat, cause="barbarian")
            return self._after_play()
        if kind == "tar":
            m = self.monsters.get(target)
            if not m or m["tar"]:
                raise IllegalMove("pick a Monster to tar")
            self._discard(seat, cid, why="play")
            m["tar"] = True
            self.events.append(Event("tar", seat=seat, mid=target))
            return self._after_play()
        if kind == "drive_back":
            m = self.monsters.get(target)
            if not m or m["ring"] == FOREST:
                raise IllegalMove("pick a Monster out of the Forest")
            self._discard(seat, cid, why="play")
            frm = m["ring"]
            m["ring"] = FOREST
            self.events.append(Event("driven", seat=seat, mid=target, arc=m["arc"], frm=frm))
            return self._after_play()
        if kind == "fortify":
            if target is None or not (0 <= target < ARCS) or not self.walls[target] or self.fortified[target]:
                raise IllegalMove("pick a standing Wall that isn't fortified")
            self._discard(seat, cid, why="play")
            self.fortified[target] = True
            self.events.append(Event("fortify", seat=seat, arc=target))
            return self._after_play()
        if kind == "missing":
            if self.no_monsters:
                raise IllegalMove("already played")
            self._discard(seat, cid, why="play")
            self.no_monsters = True
            self.events.append(Event("missing", seat=seat))
            return self._after_play()
        if kind == "draw2":
            self._discard(seat, cid, why="play")
            self.events.append(Event("draw2", seat=seat))
            self._draw_card(seat)
            self._draw_card(seat)
            return self._after_play()
        if kind == "scavenge":
            if target not in self.discard_pile:
                raise IllegalMove("pick a card from the discard pile")
            self._discard(seat, cid, why="play")
            self.discard_pile.remove(target)
            self.hands[seat].append(target)
            self.events.append(Event("scavenge", seat=seat, card=target))
            return self._after_play()
        raise IllegalMove("unknown card")

    def _build(self, seat, cid, other, arc):
        kinds = {self.cards[cid]["kind"], self.cards[other]["kind"] if other in self.cards else None}
        if other not in self.hands[seat] or kinds != {"brick", "mortar"}:
            raise IllegalMove("a Wall takes a Brick and a Mortar")
        if arc is None or not 0 <= arc < ARCS or self.walls[arc]:
            raise IllegalMove("pick a Wall that has fallen")
        self._discard(seat, cid, why="play")
        self._discard(seat, other, why="play")
        self.walls[arc] = True
        self.events.append(Event("build", seat=seat, arc=arc))
        return self._after_play()

    def _after_play(self):
        self._check_end()
        return True

    # -------------------------------------------------------------------------------- monsters

    def _spawn(self, kind, arc, ring=FOREST):
        m = {"id": self.next_mid, "kind": kind, "hp": HP[kind], "max": HP[kind], "arc": arc, "ring": ring,
             "tar": False}
        self.next_mid += 1
        self.monsters[m["id"]] = m
        self.events.append(Event("spawn", mid=m["id"], kind=kind, arc=arc, ring=ring, hp=m["hp"]))
        return m

    def _damage(self, m, amount, by=None, cause=""):
        """Take `amount` points off Monster m; slain at 0 (a trophy for seat `by`, if a player did it)."""
        m["hp"] = max(0, m["hp"] - amount)
        slain = m["hp"] == 0
        self.events.append(Event("damage", mid=m["id"], amount=amount, hp=m["hp"], by=by, cause=cause,
                                 slain=slain))
        if slain:
            del self.monsters[m["id"]]
            if by is not None:
                self.trophies[by].append(m["kind"])
            else:
                self.monster_discard.append(m["kind"])
            self.events.append(Event("slain", mid=m["id"], kind=m["kind"], by=by, cause=cause))
        return slain

    def _move(self, ms, how="in", why="move"):
        """Move Monsters ms together: "in" one ring closer (clockwise in the Castle ring), "cw"/"ccw" around their
        ring. Walls and Towers are attacked as the rules say: one Monster in a group takes the damage, all stay."""
        ms = [m for m in ms if not m["tar"] and m["id"] in self.monsters]
        if not ms:
            return
        self.events.append(Event("move_begin", why=why))
        into_castle = {}  # castle arc -> Monsters arriving there this move
        at_walls = [m for m in ms if how == "in" and m["ring"] == SWORDSMAN]  # by arc, as a group per Wall
        for m in sorted(ms, key=lambda m: m["id"]):
            arc, ring = m["arc"], m["ring"]
            if m in at_walls:
                continue
            if how == "in":
                if ring == CASTLE:
                    to = ((arc + 1) % ARCS, CASTLE)
                else:
                    to = (arc, ring - 1)
            else:
                to = ((arc + (1 if how == "cw" else -1)) % ARCS, ring)
            self.events.append(Event("move", mid=m["id"], frm=(arc, ring), to=to))
            m["arc"], m["ring"] = to
            if to[1] == CASTLE:
                into_castle.setdefault(to[0], []).append(m)
        if how == "in":
            for arc in range(ARCS):
                group = [m for m in at_walls if m["arc"] == arc and m["id"] in self.monsters]
                if not group:
                    continue
                if self.walls[arc]:
                    victim = self._choose_victim(group)
                    if self.fortified[arc]:
                        self.fortified[arc] = False
                        self.events.append(Event("wall_hit", arc=arc, mid=victim["id"], fortified=True,
                                                 mids=[m["id"] for m in group]))
                    else:
                        self.walls[arc] = False
                        self.events.append(Event("wall_hit", arc=arc, mid=victim["id"], fortified=False,
                                                 mids=[m["id"] for m in group]))
                    self._damage(victim, 1, cause="wall")
                else:
                    for m in group:
                        self.events.append(Event("move", mid=m["id"], frm=(arc, SWORDSMAN), to=(arc, CASTLE)))
                        m["ring"] = CASTLE
                        into_castle.setdefault(arc, []).append(m)
        for arc, group in sorted(into_castle.items()):
            group = [m for m in group if m["id"] in self.monsters]
            if group and self.towers[arc]:
                self.towers[arc] = False
                victim = self._choose_victim(group)
                self.events.append(Event("tower_hit", arc=arc, mid=victim["id"], mids=[m["id"] for m in group]))
                self._damage(victim, 1, cause="tower")
                if not any(self.towers):
                    self._check_end()
                    return
        self.events.append(Event("move_end"))

    def _choose_victim(self, group):
        """The players choose which Monster takes the damage: one it slays if any, else the strongest."""
        dying = [m for m in group if m["hp"] == 1]
        if dying:
            return max(dying, key=lambda m: POINTS[m["kind"]])
        return max(group, key=lambda m: (m["hp"], m["id"]))

    def _boulder(self):
        arc = self.rng.randrange(ARCS)
        opp = (arc + 3) % ARCS
        path = []  # where it rolls, in order, and what it smashes there

        def crush(a, ring):
            for m in sorted(self.monsters_at(a, ring), key=lambda m: m["id"]):
                path.append(("crush", a, ring, m["id"]))

        stop = None
        for ring in (FOREST, ARCHER, KNIGHT, SWORDSMAN):
            crush(arc, ring)
        if self.fortified[arc]:
            stop = ("fortify", arc)
        elif self.walls[arc]:
            stop = ("wall", arc)
        if not stop:
            crush(arc, CASTLE)
            if self.towers[arc]:
                stop = ("tower", arc)
        if not stop:
            crush(opp, CASTLE)
            if self.towers[opp]:
                stop = ("tower", opp)
        if not stop:
            if self.fortified[opp]:
                stop = ("fortify", opp)
            elif self.walls[opp]:
                stop = ("wall", opp)
        if not stop:
            for ring in (SWORDSMAN, KNIGHT, ARCHER, FOREST):
                crush(opp, ring)
        self.events.append(Event("boulder", arc=arc, stop=list(stop) if stop else None,
                                 crushed=[p[3] for p in path]))
        for _, a, ring, mid in path:
            m = self.monsters.get(mid)
            if m:
                self._damage(m, m["hp"], cause="boulder")
        if stop:
            what, a = stop
            if what == "fortify":
                self.fortified[a] = False
            elif what == "wall":
                self.walls[a] = False
            else:
                self.towers[a] = False
        self._check_end()

    def _resolve_token(self, kind):
        self.events.append(Event("token", kind=kind))
        if kind in HP:
            arc = self.rng.randrange(ARCS)
            self.events.append(Event("roll", value=arc + 1))
            m = self._spawn(kind, arc)
            if kind in BOSSES:
                self.events.append(Event("boss_power", kind=kind, mid=m["id"]))
            if kind == "goblin_king":
                self.to_draw += 3
            elif kind == "orc_warlord":
                color = arc_color(arc)
                self._move([x for x in self.monsters.values() if arc_color(x["arc"]) == color], why=kind)
            elif kind == "troll_mage":
                self._move(list(self.monsters.values()), why=kind)
            elif kind == "healer":
                for x in self.monsters.values():
                    if x["hp"] < x["max"]:
                        x["hp"] += 1
                        self.events.append(Event("heal", mid=x["id"], hp=x["hp"]))
            del m
            return
        self.monster_discard.append(kind)
        if kind == "boulder":
            self._boulder()
        elif kind.startswith("move_") and kind[5:] in COLORS:
            arcs = arcs_of(kind[5:])
            self._move([m for m in self.monsters.values() if m["arc"] in arcs], why=kind)
        elif kind in ("move_cw", "move_ccw"):
            self._move(list(self.monsters.values()), how=kind[5:], why=kind)
        elif kind.startswith("plague_"):
            victim = kind[7:]
            for seat in range(self.players):
                for cid in [c for c in self.hands[seat] if self.cards[c]["kind"] == victim]:
                    self._discard(seat, cid, why="plague")
        elif kind == "discard1":
            for seat in range(self.players):
                if self.hands[seat]:
                    self.pending[seat] = "discard1"
        elif kind == "draw3":
            self.to_draw += 3
        elif kind == "draw4":
            self.to_draw += 4

    def forced_discard(self, seat, cid):
        """Answer "All Players Discard 1 Card"."""
        if self.pending.get(seat) != "discard1":
            raise IllegalMove("nothing to discard")
        if cid not in self.hands[seat]:
            raise IllegalMove("not in your hand")
        self._discard(seat, cid, why="discard1")
        del self.pending[seat]
        if not self.pending:
            self._run_monsters()

    def _monsters_move(self):
        """Step 5: every Monster moves one space in."""
        self.phase = "move"
        self.events.append(Event("monster_phase", seat=self.current))
        self._move(list(self.monsters.values()))

    def _draw_monsters(self):
        """Step 6: draw 2 Monster tokens (none if Missing was played), then the next player's turn begins."""
        self.phase = "draw_monsters"
        self.to_draw = 0 if self.no_monsters else 2
        self.events.append(Event("draw_monsters", seat=self.current, count=self.to_draw))
        if self.no_monsters:
            self.events.append(Event("no_draw"))
        self._run_monsters()

    def end_turn(self, seat):
        """Skip ahead through the steps that remain: the Monsters move, new ones are drawn, the next turn begins."""
        self._check(seat)
        turn = self.turn
        while self.turn == turn and self.phase != "over" and not self.pending:
            self.next_step(seat)

    def _run_monsters(self):
        while self.to_draw > 0 and self.pile and self.phase != "over":
            self.to_draw -= 1
            self._resolve_token(self.pile.pop())
            if self.pending:
                return  # players must discard first; forced_discard() carries on
        if self._check_end():
            return
        self.current = (self.current + 1) % self.players
        self._begin_turn()

    def _check_end(self):
        if self.phase == "over":
            return True
        if not any(self.towers):
            self.phase, self.result = "over", "lost"
            self.pending.clear()
            self.events.append(Event("game_over", result="lost"))
            return True
        if not self.pile and not self.monsters and not self.pending:
            self.phase, self.result = "over", "won"
            self.events.append(Event("game_over", result="won", winner=self.master_slayer()))
            return True
        return False

    def master_slayer(self):
        """The seat with the most points (ties: most Monsters slain), or None in a tie still."""
        best = sorted(range(self.players), key=lambda s: (self.score(s), len(self.trophies[s])), reverse=True)
        if len(best) > 1 and (self.score(best[0]), len(self.trophies[best[0]])) == \
                (self.score(best[1]), len(self.trophies[best[1]])):
            return None
        return best[0]

    def take_events(self):
        ev, self.events = self.events, []
        return ev


def apply(game, seat, action):
    """Carry out an action dict from a player (UI, bot or network): {"a": "next"|"discard"|"offer"|"answer"|
    "cancel"|"play"|"end"|"forced_discard", ...}. Raises IllegalMove if it isn't allowed."""
    a = action.get("a")
    if a == "next":
        return game.next_step(seat)
    if a == "discard":
        return game.discard(seat, action["card"])
    if a == "offer":
        return game.offer_trade(seat, action["to"], action["give"], action["take"])
    if a == "answer":
        return game.answer_trade(seat, bool(action["accept"]))
    if a == "cancel":
        return game.cancel_trade(seat)
    if a == "play":
        return game.play(seat, action["card"], action.get("target"), action.get("extra"))
    if a == "end":
        return game.end_turn(seat)
    if a == "forced_discard":
        return game.forced_discard(seat, action["card"])
    raise IllegalMove(f"unknown action {a!r}")
