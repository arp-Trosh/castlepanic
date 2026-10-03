"""Computer players: a greedy defender that plays whatever does the most good right now, and trades with open
hands for the cards that let it.

`next_action(game, seat)` returns the bot's next move as an action dict (the same shape a human's UI sends, see
`session.apply_action`), or None when the bot has nothing to do. Bots also answer trades and forced discards.
"""
from .rules import CASTLE, FOREST, HIT_RING, KNIGHT, SWORDSMAN, ARCHER, POINTS

HIT_KINDS = ("archer", "knight", "swordsman", "hero")


def threat(m, game=None):
    """How soon a Monster hurts the Castle, and how badly."""
    near = {CASTLE: 10, SWORDSMAN: 6, KNIGHT: 3, ARCHER: 1.5, FOREST: 0.5}[m["ring"]]
    if game is not None and m["ring"] == SWORDSMAN and not game.walls[m["arc"]]:
        near = 9 if game.towers[m["arc"]] else 7
    return near * (1 + 0.4 * m["hp"]) + 0.3 * POINTS[m["kind"]]


def card_value(game, card, seat=None):
    """Rough worth of a card in hand right now (higher is keep)."""
    kind, color = card["kind"], card["color"]
    ms = list(game.monsters.values())
    if kind in HIT_KINDS:
        hits = [m for m in ms if game.can_hit(card, m)]
        soon = [m for m in ms if m["ring"] != CASTLE and (kind == "hero" or m["ring"] - 1 == HIT_RING[kind]) and
                (color == "any" or kind == "hero" or game.can_hit({"kind": "hero", "color": color}, m))]
        base = 2.0 if color == "any" or kind == "hero" else 1.0
        return base + 3 * len(hits) + max((threat(m) for m in hits), default=0) * 0.3 + 0.7 * len(soon)
    if kind == "barbarian":
        return 9
    if kind in ("brick", "mortar"):
        other = "mortar" if kind == "brick" else "brick"
        down = 6 - sum(game.walls)
        paired = seat is not None and any(game.cards[c]["kind"] == other for c in game.hands[seat])
        return (4 + 3 * down) if paired else (0.5 + 1.0 * down)
    if kind == "nice_shot":
        return 4
    if kind in ("tar", "drive_back"):
        return 5 + (3 if any(m["ring"] == CASTLE for m in ms) else 0)
    if kind == "fortify":
        return 3
    if kind == "missing":
        return 4
    return 3.5  # draw2, scavenge


def worst_card(game, seat):
    hand = game.hand(seat)
    return min(hand, key=lambda c: card_value(game, c, seat))["id"] if hand else None


def best_play(game, seat):
    """The most useful single play now, as an action dict, or None."""
    hand = game.hand(seat)
    by_kind = {}
    for c in hand:
        by_kind.setdefault(c["kind"], []).append(c)
    ms = sorted(game.monsters.values(), key=lambda m: threat(m, game), reverse=True)
    options = []  # (score, action)

    if "brick" in by_kind and "mortar" in by_kind and not all(game.walls):
        # rebuild where the Monsters are thickest
        arc = max((a for a in range(6) if not game.walls[a]),
                  key=lambda a: sum(threat(m) for m in ms if m["arc"] == a and m["ring"] != CASTLE))
        danger = sum(threat(m) for m in ms if m["arc"] == arc and m["ring"] != CASTLE)
        options.append((8 + danger, dict(a="play", card=by_kind["brick"][0]["id"], target=arc,
                                         extra=by_kind["mortar"][0]["id"])))
    for c in hand:
        kind = c["kind"]
        if kind in HIT_KINDS:
            for m in ms:
                if game.can_hit(c, m):
                    kill = m["hp"] == 1
                    score = threat(m) * (1.6 if kill else 1.0) + (POINTS[m["kind"]] if kill else 0)
                    # save the flexible cards for when they're needed
                    score -= 1.5 if c["color"] == "any" or kind == "hero" else 0
                    options.append((score, dict(a="play", card=c["id"], target=m["id"])))
                    if "nice_shot" in by_kind and m["hp"] >= 2:
                        options.append((threat(m) * 1.8 + POINTS[m["kind"]], dict(
                            a="play", card=by_kind["nice_shot"][0]["id"], target=m["id"], extra=c["id"])))
        elif kind == "barbarian":
            for m in ms:
                if m["ring"] <= SWORDSMAN and m["hp"] >= 2 or m["ring"] == CASTLE:
                    options.append((threat(m) * 1.5 + POINTS[m["kind"]], dict(a="play", card=c["id"], target=m["id"])))
        elif kind == "drive_back":
            for m in ms:
                if m["ring"] == CASTLE or (m["ring"] == SWORDSMAN and m["hp"] >= 2 and not game.walls[m["arc"]]):
                    options.append((threat(m) * 1.2, dict(a="play", card=c["id"], target=m["id"])))
        elif kind == "tar":
            for m in ms:
                if not m["tar"] and (m["ring"] == CASTLE or (m["ring"] == SWORDSMAN and not game.walls[m["arc"]])):
                    options.append((threat(m) * 0.8, dict(a="play", card=c["id"], target=m["id"])))
        elif kind == "fortify":
            arcs = [a for a in range(6) if game.walls[a] and not game.fortified[a]]
            if arcs:
                a = max(arcs, key=lambda a: sum(threat(m) for m in ms if m["arc"] == a and m["ring"] in (SWORDSMAN, KNIGHT)))
                if any(m["arc"] == a and m["ring"] in (SWORDSMAN, KNIGHT) for m in ms):
                    options.append((5, dict(a="play", card=c["id"], target=a)))
        elif kind == "draw2":
            options.append((6, dict(a="play", card=c["id"])))
        elif kind == "scavenge" and game.discard_pile:
            pick = max(game.discard_pile, key=lambda cid: card_value(game, game.cards[cid], seat))
            options.append((5.5, dict(a="play", card=c["id"], target=pick)))
        elif kind == "missing" and not game.no_monsters:
            pressure = sum(threat(m) for m in ms)
            if pressure > 25 or len(game.pile) <= 2:
                options.append((pressure * 0.2, dict(a="play", card=c["id"])))
    if not options:
        return None
    return max(options, key=lambda o: o[0])[1]


# a teammate's gain on their own turn, against the board's score now: games played out by bots win most at
# 0-0.2 (39% of 900 games, 1-6 players; 32% at 0.5, 17% at 3), as what they'd do with it once the Monsters have
# moved is a rougher guess than what playing it now does; so it mostly breaks ties
LATER_WEIGHT = 0.1


def _clone(game):
    """A copy to try moves on: the real game is never touched."""
    import copy
    events, game.events = game.events, []
    try:
        return copy.deepcopy(game)
    finally:
        game.events = events


def _advanced(game):
    """The board once the Monsters have moved: where a teammate, playing later, will find them."""
    g = _clone(game)
    g._move(list(g.monsters.values()))
    return g


def _plan_score(game, seat, trade=None):
    """How the board stands after this seat plays everything worth playing (having made `trade` first) and the
    Monsters move."""
    g = _clone(game)
    if trade:
        frm, to, give, take = trade
        g.hands[frm].remove(give)
        g.hands[to].remove(take)
        g.hands[frm].append(take)
        g.hands[to].append(give)
    g.phase, g.trade_offer, g.pending = "play", None, {}
    for _ in range(8):
        act = best_play(g, seat)
        if not act:
            break
        try:
            g.play(seat, act["card"], act.get("target"), act.get("extra"))
        except Exception:
            break
        if g.phase == "over":
            break
    return _evaluate(g)


def _later_gain(later, card_in, card_out, seat):
    """What a teammate gains for their own turn by taking card_in for card_out (on the board as it will be)."""
    return card_value(later, card_in, seat) - card_value(later, card_out, seat)


def trade_wish(game, seat):
    """The trade that does the team most good, or None. All hands are open, so the active player weighs both sides:
    what the card it takes lets it do now (played out on a copy of the board), and what the card it gives is worth
    to the teammate on their own turn, once the Monsters have moved."""
    if game.trades_used >= game.max_trades or game.players < 2:
        return None
    mine = game.hand(seat)
    if not mine:
        return None
    later = _advanced(game)
    # rough first pass: cards worth taking (useful to me now) and giving (little use to me, more to them)
    rough = []
    for other in range(game.players):
        if other == seat or other in game.traded_with:
            continue
        for take in game.hand(other):
            gain_now = card_value(game, take, seat) - card_value(game, take, other)
            for give in mine:
                if give["kind"] == take["kind"] and give["color"] == take["color"]:
                    continue
                score = gain_now - card_value(game, give, seat) + _later_gain(later, give, take, other)
                rough.append((score, other, give["id"], take["id"]))
    rough.sort(reverse=True)
    base = _plan_score(game, seat)
    best = None
    for _, other, give, take in rough[:8]:
        now = _plan_score(game, seat, (seat, other, give, take)) - base
        team = now + LATER_WEIGHT * _later_gain(later, game.cards[give], game.cards[take], other)
        if team > 1.0 and (best is None or team > best[0]):
            best = (team, other, give, take)
    if best is None:
        return None
    return dict(a="offer", to=best[1], give=best[2], take=best[3])


def accept_trade(game, seat):
    """Bots are team players: they take any trade that doesn't cost the team more than it gains."""
    o = game.trade_offer
    give, take = game.cards[o["take"]], game.cards[o["give"]]  # what this bot gives up, and gets
    now = card_value(game, give, o["from"]) - card_value(game, take, o["from"])
    later = _later_gain(_advanced(game), take, give, seat)
    return now + later > -1.0


def next_action(game, seat, offered=None):
    """The bot's next move. offered: trades already tried this turn (to not repeat a declined one)."""
    if game.phase == "over":
        return None
    if game.pending.get(seat) == "discard1":
        return dict(a="forced_discard", card=worst_card(game, seat))
    if game.trade_offer:
        if game.trade_offer["to"] == seat:
            return dict(a="answer", accept=accept_trade(game, seat))
        return None
    if game.pending or seat != game.current:
        return None
    if game.phase == "discard":
        worst = worst_card(game, seat)
        if game.discards_used < game.max_discards and worst is not None and \
                card_value(game, game.cards[worst], seat) < 3:
            return dict(a="discard", card=worst)
        return dict(a="next")
    if game.phase == "trade":
        wish = trade_wish(game, seat)
        if wish and (offered is None or (wish["give"], wish["take"]) not in offered):
            if offered is not None:
                offered.add((wish["give"], wish["take"]))
            return wish
        return dict(a="next")
    if game.phase == "play":
        play = best_play(game, seat)
        return play or dict(a="next")
    if game.phase in ("draw_up", "move"):
        return dict(a="next")
    return None


# ------------------------------------------------------------------------------------------------ lookahead

def _evaluate(game):
    """How good a position is for the defenders once the Monsters have moved: towers above all, then walls, then
    the Monsters' remaining strength weighted by how close they are."""
    import copy
    g = copy.copy(game)
    g.monsters = {k: dict(v) for k, v in game.monsters.items()}
    g.walls, g.towers, g.fortified = list(game.walls), list(game.towers), list(game.fortified)
    g.trophies = [list(t) for t in game.trophies]
    g.monster_discard = list(game.monster_discard)
    g.events = []
    g.phase = "monsters"
    g._move(list(g.monsters.values()))
    score = 30 * sum(g.towers) + 6 * sum(g.walls) + 2 * sum(g.fortified)
    near = {CASTLE: 6, SWORDSMAN: 4, KNIGHT: 2, ARCHER: 1, FOREST: 0.5}
    for m in g.monsters.values():
        wall_open = m["ring"] == SWORDSMAN and not g.walls[m["arc"]]
        score -= m["hp"] * (near[m["ring"]] + (3 if wall_open else 0))
    return score


def lookahead_play(game, seat):
    """The play whose result, after the Monsters' next move, scores best; None if holding is as good."""
    import copy
    options = []
    hand = game.hand(seat)
    base = _evaluate(game)
    seen = set()
    for c in hand:
        kind = c["kind"]
        acts = []
        t = game.targets(c["id"])
        if t:
            acts += [dict(a="play", card=c["id"], target=m) for m in t]
            if kind in HIT_KINDS:
                ns = next((x for x in hand if x["kind"] == "nice_shot"), None)
                if ns:
                    acts += [dict(a="play", card=ns["id"], target=m, extra=c["id"]) for m in t
                             if game.monsters[m]["hp"] >= 2]
        for a in acts:
            key = (game.cards[a["card"]]["kind"], game.cards[a["card"]]["color"], a.get("target"), a.get("extra") is not None)
            if key in seen:
                continue
            seen.add(key)
            g = copy.copy(game)
            g.monsters = {k: dict(v) for k, v in game.monsters.items()}
            g.hands = [list(h) for h in game.hands]
            g.trophies = [list(x) for x in game.trophies]
            g.discard_pile, g.events = list(game.discard_pile), []
            g.monster_discard = list(game.monster_discard)
            g.walls, g.towers, g.fortified = list(game.walls), list(game.towers), list(game.fortified)
            try:
                g.play(seat, a["card"], a.get("target"), a.get("extra"))
            except Exception:
                continue
            gain = _evaluate(g) - base
            # spend the precious cards only for real gains
            cost = {"barbarian": 6, "nice_shot": 3, "drive_back": 3, "tar": 2}.get(kind, 0)
            if c["color"] == "any" or kind == "hero":
                cost += 1
            if a.get("extra") is not None:
                cost += 3
            options.append((gain - cost, a))
    if not options:
        return None
    gain, act = max(options, key=lambda o: o[0])
    return act if gain > 0 else None


_greedy_best_play = best_play


def best_play(game, seat):
    """Hit, slay and hold with the lookahead; build, fortify, draw and the rest by rule of thumb."""
    act = lookahead_play(game, seat)
    rule = _greedy_best_play(game, seat)
    if rule and game.cards[rule["card"]]["kind"] in ("brick", "mortar", "fortify", "draw2", "scavenge", "missing"):
        return rule
    return act or rule
