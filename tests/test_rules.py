import json
import unittest

from castlepanic import bots
from castlepanic.rules import (ARCHER, CASTLE, FOREST, KNIGHT, SWORDSMAN, Game, IllegalMove, apply)


def play_out(game, limit=5000):
    offered = {s: set() for s in range(game.players)}
    last_turn = game.turn
    for _ in range(limit):
        if game.phase == "over":
            return game
        if game.turn != last_turn:
            offered = {s: set() for s in range(game.players)}
            last_turn = game.turn
        seats = [s for s in game.pending] or ([game.trade_offer["to"]] if game.trade_offer else [game.current])
        seat = seats[0]
        act = bots.next_action(game, seat, offered[seat])
        apply(game, seat, act)
        check_invariants(game)
    raise AssertionError("game didn't finish")


def check_invariants(game):
    held = sum(len(h) for h in game.hands)
    assert held + len(game.deck) + len(game.discard_pile) == 49, "cards lost"
    ids = [c for h in game.hands for c in h] + game.deck + game.discard_pile
    assert len(set(ids)) == 49, "card duplicated"
    tokens = len(game.pile) + len(game.monsters) + len(game.monster_discard) + sum(map(len, game.trophies))
    assert tokens == 49, f"tokens lost: {tokens}"
    for m in game.monsters.values():
        assert 1 <= m["hp"] <= m["max"]
        assert 0 <= m["arc"] < 6 and CASTLE <= m["ring"] <= FOREST


class Rules(unittest.TestCase):
    def test_setup(self):
        g = Game(["a", "b", "c"], seed=1)
        self.assertEqual(len(g.monsters), 6)
        self.assertTrue(all(m["ring"] == ARCHER for m in g.monsters.values()))
        self.assertEqual(sorted(m["arc"] for m in g.monsters.values()), list(range(6)))
        self.assertEqual([len(h) for h in g.hands], [5, 5, 5])
        self.assertEqual(Game(["solo"], seed=1).hand_size, 6)
        self.assertEqual(Game(list("abcdef"), seed=1).hand_size, 4)
        check_invariants(g)

    def test_hit_rules(self):
        g = Game(["a", "b"], seed=2)
        m = next(iter(g.monsters.values()))
        m.update(arc=0, ring=KNIGHT)
        self.assertTrue(g.can_hit({"kind": "knight", "color": "red"}, m))
        self.assertFalse(g.can_hit({"kind": "knight", "color": "green"}, m))
        self.assertTrue(g.can_hit({"kind": "knight", "color": "any"}, m))
        self.assertFalse(g.can_hit({"kind": "archer", "color": "red"}, m))
        self.assertTrue(g.can_hit({"kind": "hero", "color": "red"}, m))
        m["ring"] = CASTLE
        self.assertFalse(g.can_hit({"kind": "hero", "color": "red"}, m))

    def test_wall_then_tower(self):
        g = Game(["a"], seed=3)
        for m in list(g.monsters.values()):
            del g.monsters[m["id"]]
        orc = g._spawn("orc", 2, SWORDSMAN)
        g._move([orc])
        self.assertFalse(g.walls[2])
        self.assertEqual(orc["hp"], 1)
        self.assertEqual(orc["ring"], SWORDSMAN)
        g._move([orc])  # no wall now: into the Castle, smashing the Tower, and dies of it
        self.assertFalse(g.towers[2])
        self.assertNotIn(orc["id"], g.monsters)

    def test_fortify_saves_wall(self):
        g = Game(["a"], seed=3)
        g.monsters.clear()
        g.fortified[1] = True
        troll = g._spawn("troll", 1, SWORDSMAN)
        g._move([troll])
        self.assertTrue(g.walls[1])
        self.assertFalse(g.fortified[1])
        self.assertEqual(troll["hp"], 2)

    def test_group_attack_hurts_one(self):
        g = Game(["a"], seed=4)
        g.monsters.clear()
        a, b = g._spawn("troll", 0, SWORDSMAN), g._spawn("troll", 0, SWORDSMAN)
        g._move([a, b])
        self.assertEqual(sorted([a["hp"], b["hp"]]), [2, 3])

    def test_castle_ring_moves_clockwise(self):
        g = Game(["a"], seed=5)
        g.monsters.clear()
        g.towers[1] = False
        t = g._spawn("troll", 0, CASTLE)
        g.towers[0] = False
        g._move([t])
        self.assertEqual((t["arc"], t["ring"]), (1, CASTLE))
        g._move([t])
        self.assertEqual(t["arc"], 2)
        self.assertFalse(g.towers[2])
        self.assertEqual(t["hp"], 2)

    def test_tar_holds(self):
        g = Game(["a"], seed=6)
        m = next(iter(g.monsters.values()))
        m["tar"] = True
        g._move([m])
        self.assertEqual(m["ring"], ARCHER)

    def test_boulder_stops_at_wall(self):
        g = Game(["a"], seed=7)
        g.monsters.clear()
        g.rng.randrange = lambda n: 3
        victim = g._spawn("troll", 3, KNIGHT)
        safe = g._spawn("goblin", 0, KNIGHT)  # the opposite arc, beyond the wall
        g._boulder()
        self.assertNotIn(victim["id"], g.monsters)
        self.assertIn(safe["id"], g.monsters)
        self.assertFalse(g.walls[3])
        self.assertTrue(g.towers[3])

    def test_boulder_rolls_through(self):
        g = Game(["a"], seed=7)
        g.monsters.clear()
        g.rng.randrange = lambda n: 3
        g.walls[3] = g.towers[3] = g.towers[0] = g.walls[0] = False
        far = g._spawn("orc", 0, FOREST)
        g._boulder()
        self.assertNotIn(far["id"], g.monsters)

    def test_boss_power_only_for_bosses(self):
        g = Game(["a"], seed=7)
        g.take_events()
        g._resolve_token("orc")
        self.assertNotIn("boss_power", [e["e"] for e in g.take_events()])
        g._resolve_token("healer")
        self.assertIn("boss_power", [e["e"] for e in g.take_events()])

    def test_illegal(self):
        g = Game(["a", "b"], seed=8)
        with self.assertRaises(IllegalMove):
            apply(g, 1, {"a": "end"})
        with self.assertRaises(IllegalMove):
            apply(g, 0, {"a": "play", "card": g.hands[1][0]})

    def test_steps_in_order(self):
        g = Game(["a", "b"], seed=10)
        self.assertEqual(g.phase, "discard")  # Draw Up moves on by itself
        self.assertIn({"e": "step", "seat": 0, "step": "discard"}, g.take_events())
        hit = next(c for c in g.hands[0])
        with self.assertRaises(IllegalMove):  # nothing is played before step 4
            apply(g, 0, {"a": "play", "card": hit})
        apply(g, 0, {"a": "discard", "card": g.hands[0][0]})
        with self.assertRaises(IllegalMove):  # one discard
            apply(g, 0, {"a": "discard", "card": g.hands[0][0]})
        self.assertEqual(len(g.hands[0]), 6)
        apply(g, 0, {"a": "next"})
        self.assertEqual(g.phase, "trade")
        apply(g, 0, {"a": "offer", "to": 1, "give": g.hands[0][0], "take": g.hands[1][0]})
        apply(g, 1, {"a": "answer", "accept": True})
        with self.assertRaises(IllegalMove):  # one trade
            apply(g, 0, {"a": "offer", "to": 1, "give": g.hands[0][0], "take": g.hands[1][0]})
        apply(g, 0, {"a": "next"})
        self.assertEqual(g.phase, "play")
        rings = {m["id"]: m["ring"] for m in g.monsters.values()}
        apply(g, 0, {"a": "next"})
        self.assertEqual(g.phase, "move")
        self.assertTrue(all(m["ring"] == rings[m["id"]] - 1 for m in g.monsters.values()))
        pile = len(g.pile)
        g.take_events()
        apply(g, 0, {"a": "next"})
        ev = [e["e"] for e in g.take_events()]
        self.assertIn("draw_monsters", ev)
        self.assertLess(len(g.pile), pile)
        if not g.pending:
            self.assertEqual((g.current, g.phase), (1, "discard"))
            self.assertEqual(len(g.hands[1]), g.hand_size)

    def test_solo_two_discards_no_trade(self):
        g = Game(["solo"], seed=11)
        apply(g, 0, {"a": "discard", "card": g.hands[0][0]})
        apply(g, 0, {"a": "discard", "card": g.hands[0][0]})
        with self.assertRaises(IllegalMove):
            apply(g, 0, {"a": "discard", "card": g.hands[0][0]})
        apply(g, 0, {"a": "next"})
        self.assertEqual(g.phase, "play")

    def test_six_players_trade_with_two(self):
        g = Game(list("abcdef"), seed=12)
        apply(g, 0, {"a": "next"})
        apply(g, 0, {"a": "offer", "to": 1, "give": g.hands[0][0], "take": g.hands[1][0]})
        apply(g, 1, {"a": "answer", "accept": True})
        with self.assertRaises(IllegalMove):  # the second trade is with someone else
            apply(g, 0, {"a": "offer", "to": 1, "give": g.hands[0][0], "take": g.hands[1][0]})
        apply(g, 0, {"a": "offer", "to": 2, "give": g.hands[0][0], "take": g.hands[2][0]})
        apply(g, 2, {"a": "answer", "accept": True})
        with self.assertRaises(IllegalMove):  # and that's all
            apply(g, 0, {"a": "offer", "to": 3, "give": g.hands[0][0], "take": g.hands[3][0]})

    def test_json_round_trip(self):
        g = Game(["a", "b", "c"], seed=9)
        d = json.loads(json.dumps(g.to_dict(hide_pile=False)))
        h = Game.from_dict(d)
        self.assertEqual(h.to_dict(hide_pile=False), g.to_dict(hide_pile=False))
        json.dumps(g.to_dict())

    def test_bot_games_finish(self):
        results = {"won": 0, "lost": 0}
        for seed in range(300):
            n = 1 + seed % 6
            g = play_out(Game([f"p{i}" for i in range(n)], seed=seed))
            results[g.result] += 1
        print("\nbot games:", results)
        self.assertGreater(results["won"], 0)
        self.assertGreater(results["lost"], 0)


if __name__ == "__main__":
    unittest.main()
