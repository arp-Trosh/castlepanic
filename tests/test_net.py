import time
import unittest

from castlepanic.session import ClientSession, HostSession


def pump(host, client, secs=1.0, until=None):
    end = time.time() + secs
    hev, cev = [], []
    while time.time() < end:
        hev += host.poll(0.05)
        cev += client.poll(0.05)
        if until and until():
            break
        time.sleep(0.01)
    return hev, cev


class Net(unittest.TestCase):
    def test_lobby_game_chat(self):
        host = HostSession("Hostess", max_players=3, bots_on=True, port=0, seed=4)
        host.bot_delay = 0.0
        client = ClientSession("Guest", "127.0.0.1", host.port)
        try:
            pump(host, client, 2, until=lambda: len(client.seats) == 2)
            self.assertEqual([s["name"] for s in client.seats], ["Hostess", "Guest"])
            host.start()
            pump(host, client, 2, until=lambda: client.game is not None)
            self.assertEqual(client.my_seat, 1)
            self.assertEqual(len(client.game.names), 3)  # a bot filled the third seat
            client.chat("hello there")
            pump(host, client, 1, until=lambda: any("hello there" in t for t, _ in host.log))
            self.assertTrue(any("Guest: hello there" in t for t, _ in host.log))
            host.chat("welcome")
            pump(host, client, 1, until=lambda: any("Hostess: welcome" in t for t, _ in client.log))
            pump(host, client, 0.2)  # (the guest's own line, echoed back)
            self.assertEqual((host.heard, client.heard), (1, 1))  # each chimes for the other's line, not their own
            # host ends turn; bot plays; then it's the guest's turn: guest ends turn over the network
            host.act({"a": "end"})
            pump(host, client, 5, until=lambda: client.game.current == 1)
            self.assertEqual(client.game.current, 1)
            client.act({"a": "end"})
            # the bot then plays at once until it needs the host (its turn, or a trade the bot offers it; the guest
            # turns down any it is offered): wait for
            # that, and for the client to hear all of it (comparing as soon as the host moved on raced the update)
            answered = []

            def waiting_on(g):
                return list(g.pending) or ([g.trade_offer["to"]] if g.trade_offer else [g.current])

            def in_step():
                g = client.game
                if g.trade_offer and g.trade_offer["to"] == 1 and not answered:  # the bot asks the guest for a card
                    answered.append(1)
                    client.act({"a": "answer", "accept": False})
                elif not g.trade_offer:
                    answered.clear()
                return (waiting_on(host.game) == [0] and waiting_on(client.game) == [0]
                        and (client.game.turn, client.game.phase) == (host.game.turn, host.game.phase))

            pump(host, client, 5, until=in_step)
            self.assertEqual(waiting_on(host.game), [0])
            self.assertEqual(waiting_on(client.game), [0])
            self.assertEqual((client.game.turn, client.game.phase), (host.game.turn, host.game.phase))
            # a client trying to act out of turn gets an error, not a crash
            client.act({"a": "end"})
            pump(host, client, 1)
        finally:
            client.close()
            host.close()

    def test_disconnect_becomes_bot(self):
        host = HostSession("H", max_players=2, bots_on=False, port=0, seed=1)
        client = ClientSession("G", "127.0.0.1", host.port)
        pump(host, client, 2, until=lambda: len(host.seats) == 2)
        host.start()
        pump(host, client, 1, until=lambda: client.game is not None)
        client.close()
        end = time.time() + 2
        while time.time() < end and host.seats[1]["kind"] != "bot":
            host.poll(0.05)
            time.sleep(0.01)
        self.assertEqual(host.seats[1]["kind"], "bot")
        host.close()


if __name__ == "__main__":
    unittest.main()
