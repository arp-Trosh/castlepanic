"""Every event told in words, for the game log (so all the 3D shows is also written out)."""
from .rules import RING_NAMES, TOKEN_TITLES, arc_color, card_title

KIND = {"goblin": "Goblin", "orc": "Orc", "troll": "Troll", "goblin_king": "Goblin King",
        "orc_warlord": "Orc Warlord", "troll_mage": "Troll Mage", "healer": "Healer"}


def where(arc, ring):
    return f"{arc_color(arc)} {arc + 1} {RING_NAMES[ring]}"


def describe(e, game, names):
    """A line of text (or None) for an event. game: the state after the events (for card and Monster names)."""
    k = e["e"]
    who = names[e["seat"]] if "seat" in e and e["seat"] is not None and e["seat"] < len(names) else ""

    def card(cid):
        c = game.cards.get(cid) if hasattr(game, "cards") else None
        return card_title(c) if c else "a card"

    kinds = getattr(game, "_kinds", {})
    if "mid" in e and "kind" in e and k == "spawn":
        kinds[e["mid"]] = e["kind"]
        game._kinds = kinds

    def mon(mid):
        m = game.monsters.get(mid) if hasattr(game, "monsters") else None
        kind = m["kind"] if m else kinds.get(mid)
        return KIND.get(kind, "Monster")

    if k == "turn":
        return f"--- Turn {e['turn']}: {who} ---"
    if k == "discard":
        if e.get("why") == "play":
            return None
        why = {"discard": "discards", "plague": "loses to the Plague", "discard1": "discards"}.get(e.get("why"), "discards")
        return f"{who} {why} {card(e['card'])}"
    if k == "draw_up":
        cards = e.get("cards") or []
        if not cards:
            return f"{who}'s hand is full: no cards to draw"
        return f"{who} draws up {len(cards)} card{'s' if len(cards) > 1 else ''}: " + ", ".join(card(c) for c in cards)
    if k == "draw2":
        return f"{who} draws 2 cards"
    if k == "offer":
        return f"{names[e['from']]} offers {card(e['give'])} to {names[e['to']]} for {card(e['take'])}"
    if k == "trade":
        return f"{names[e['from']]} and {names[e['to']]} trade"
    if k == "cancelled":
        return f"{who} takes back the trade offer"
    if k == "declined":
        return f"{names[e['to']]} declines the trade"
    if k == "attack":
        nice = " with a Nice Shot!" if e.get("nice") else ""
        return f"{who}'s {card(e['card'])} strikes the {mon(e['mid'])}{nice}"
    if k == "damage":
        if e["slain"]:
            return None
        cause = {"wall": " against the Wall", "tower": " smashing a Tower"}.get(e.get("cause"), "")
        return f"  the {mon(e['mid'])} takes {e['amount']}{cause} ({e['hp']} left)"
    if k == "slain":
        by = f" by {names[e['by']]}" if e.get("by") is not None else ""
        how = {"boulder": " crushed by the boulder", "wall": " on the Wall", "tower": " on the Tower"}.get(e.get("cause"), "")
        return f"  the {KIND.get(e['kind'], 'Monster')} is slain{how}{by}!"
    if k == "tar":
        return f"{who} pours Tar on the {mon(e['mid'])}"
    if k == "driven":
        return f"{who} drives the {mon(e['mid'])} back to the Forest"
    if k == "fortify":
        return f"{who} fortifies Wall {e['arc'] + 1}"
    if k == "build":
        return f"{who} rebuilds Wall {e['arc'] + 1}"
    if k == "missing":
        return f"{who} plays Missing: no Monsters this turn"
    if k == "scavenge":
        return f"{who} scavenges {card(e['card'])}"
    if k == "monster_phase":
        return "The Monsters advance..."
    if k == "draw_monsters" and e.get("count"):
        return "New Monsters are drawn..."
    if k == "token":
        return f"Monster token: {TOKEN_TITLES.get(e['kind'], e['kind'])}"
    if k == "spawn" and e["ring"] == 4:
        name = KIND.get(e["kind"], "Monster")
        return f"  {'an' if name[0] in 'AEIOU' else 'a'} {name} appears in the {where(e['arc'], e['ring'])}"
    if k == "wall_hit":
        return f"  Wall {e['arc'] + 1} {'holds (fortified)' if e['fortified'] else 'is smashed!'}"
    if k == "tower_hit":
        return f"  Tower {e['arc'] + 1} falls!"
    if k == "boulder":
        stop = e.get("stop")
        end = f", stopped by the {stop[0]} at {stop[1] + 1}" if stop else ", right across the board"
        return f"  A Giant Boulder rolls down arc {e['arc'] + 1}{end}"
    if k == "heal":
        return f"  the {mon(e['mid'])} heals to {e['hp']}"
    if k == "no_draw":
        return "No Monsters come this turn"
    if k == "reshuffle":
        return "The discards are shuffled into a new deck"
    if k == "game_over":
        if e["result"] == "won":
            w = e.get("winner")
            return "VICTORY! The Castle stands." + (f" Master Slayer: {names[w]}" if w is not None else " A tie for Master Slayer")
        return "DEFEAT. The last Tower has fallen."
    return None
