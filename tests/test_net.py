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
            # host ends turn; bot plays; then it's the guest's turn: guest ends turn over the network
            host.act({"a": "end"})
            pump(host, client, 5, until=lambda: client.game.current == 1)
            self.assertEqual(client.game.current, 1)
            client.act({"a": "end"})
            pump(host, client, 3, until=lambda: host.game.current != 1)
            self.assertNotEqual(host.game.current, 1)
            self.assertEqual(client.game.turn, host.game.turn)
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
