# Status (2026-10-03)

Playable end to end: `python -m castlepanic` (menu -> single player 1-6 / host / join -> game -> game over).

## Done
- **Rules** (`rules.py`): the full standard game + solo variant; JSON state for the network. A turn is six steps
  (`STEPS`), each moved on from with the `next` action (Draw Up moves on to Discard by itself): draw up, discard 1 (solo 2), trade 1 (6 players: 2, with
  one player or two), play, Monsters move, draw 2 Monsters. Tests: `tests/test_rules.py`
  (incl. 300 all-bot games checking cards/tokens are conserved), `tests/test_net.py` (lobby, start, chat, remote
  turns, out-of-turn errors, disconnect -> bot).
- **Bots** (`bots.py`): one-move lookahead for hits/slays, rules of thumb for the rest; trades read the open hands
  and play each candidate trade out on a copy of the board. Win rate ~39% overall (900 games; solo 33%, 2p 63%,
  3p 31%, 4p 42%, 5p 45%, 6p 18%), up from ~16% before the trade rework. Room to improve: planning across the team.
- **3D** (`scene.py`, `actors.py`, `fx.py`, `board.py`): painted mat + table, 36 forest props, 6 towers / walls /
  palisades, sentries fidgeting on the walls, every rules event animated (spawns walk in, defenders loose arrows or
  charge out, Hit/Die clips with blood, the Knight jousts (gallops out on a barded destrier and drives a chrome lance home as it comes into range, then wheels back; the foot knight still stands sentry on the walls), walls/towers collapse with dust and debris, the boulder rolls through and
  crushes, tar, drive back, build, heal sparkles, victory/defeat). Camera eases to the action; arrows/+/-/R steer.
  Static pieces are baked into a few meshes each (unicode3d's `Model.bake`) for speed; every piece is a
  `Model.copy()` of a model loaded once, and clips crossfade with `Clip.start(fade)`.
- **UI** (`ui.py`): menu over a live board, lobby with seats/bots/chat, game screen (status, 3D view, players with
  open hands, log, hand as card boxes, prompts, letter/click targeting, wall numbers, trade flow, help overlay H).
- **Network** (`session.py`, `net.py`): host/join, port 5555, lobby, bots fill seats, chat strip, a leaver becomes a bot.
- **Banners** (`banner.py`, `fonts.py`): 3D lettering in front of the camera. A new siege opens with three gold
  lines, the war horn (`start`), "tHe mOnsTeRs aRe CoMing!" in castle blocks, then the first six Monsters march
  in together. That announcement comes before the first new Monsters of every turn, and "Your turn. Defend the
  Castle!" at the start of yours. A Boss Monster announces its power in gold (`BOSS_BANNER` in scene.py)
  as it arrives, and a Plague! says which cards it takes ("Plague! Archers / All Archer cards / are
  discarded!"). Space/Enter/Esc hurries a banner away.
- **On the board**: ring names (Arc/Kni/Swo) on the three lines where the colours change, placed so they never
  overlap each other or a Monster's label (a line shows whole or not at all; zoomed far out, only the nearest line).
  Monster tags (GK OW TM HL TR OR GO) before the health pips (`SHOW_TAGS` in ui.py to drop them). The camera eases
  back to the whole board 1 s after the action ends. An Order of play window (bottom right): the six
  steps, the current one lit (following the animations, which run behind the state), and a NEXT STEP button.
  Brick and Mortar are chosen one after the other. Each drawn Monster token is named in gilt lettering (after
  "tHe mOnsTeRs aRe CoMing!"), then 0.5 s before it takes effect. Missing: "Missing! / No Monsters this turn / (whew!)" in gilt, with a relief
  sound ("phew" + a suspended-to-major horn chord). Monsters sharing a space shrink (85% for two, 70% for three or
  more); in a Castle space whose Tower has fallen they stand on the rubble. The Fortify palisade's stake tips stand
  just above the battlements (1.12-1.24 tall against the wall's 1.0), on thicker stakes, 1.25x the wall's length.
  "All Players Discard 1 Card" by mouse: click a card twice (or press its number). Trading by mouse: click your card and one of theirs (or their name) in the Defenders list, either way round.
  Multiplayer chat docks in the bottom bar (a Chat tab with an unread count; click or Tab slides it up over the
  view, Esc/Tab/click docks it) and chimes softly (`chat` in sound.py) for other players' messages.
- **Settings** (`settings.py`): characters, colours, frame rate, shadows, reflections, detail and quality on the menu's
  Settings screen, saved to ~/.config/castlepanic/settings.json (command-line flags win); F2-F8 still work. Detail:
  standard (the default) draws small models from simpler copies within a pixel (unicode3d 0.13.0's levels of detail,
  `Renderer.simplify` 1), high draws every model in full. Quality: auto (the default; unicode3d 0.14.0) steps the
  picture down while frames can't keep up with the frame rate (edge smoothing, detail, then sharpness; never
  shadows) and back up when they can; high keeps it as set; fast holds the lowest step. The bottom bar
  shows only the frame rate (achieved/target, clickable).
- **unicode3d v0.16.0** (0.11.0's camera parents, `DisplayControls(show=...)`, block lettering; 0.12.0-0.14.0
  faster on slow machines, 0.13.0 levels of detail, 0.14.0 automatic quality, 0.15.0 `Object3D.simplify` and
  auto quality only below 20 fps, 0.16.0 cheaper shadow filtering and bookkeeping), pinned in requirements.txt.
- **Sound** (`sound.py`): 36 synthesized sounds (numpy + numba filters), played via winsound / pw-play / paplay /
  aplay / afplay; nothing to install. `python -m castlepanic.sound` plays them all. A Plague! that takes cards
  plays a sad trombone ("wah wah wahhh", `plague`) with its first discard; the Knight's charge, a war-cry over hoofbeats (`joust`).
- **Assets**: 22 models by Blender scripts in `assets/src/` (kit + STYLE.md), exported to `castlepanic/data/models/`.
  Tools: `tools/preview.py` (terminal-accurate contact sheets), `tools/scene_game.py` (bot game through the scene,
  off-screen), `tools/ui_test.py` (scripted UI run with screenshots).

## Next
- Performance (unicode3d v0.10.0, 2026-10-03): a 5-turn solo game at 170x50 (8 Monsters, ~640 parts) takes
  30 ms a frame (median; 35 ms p90, 60 ms worst), against 43 ms (637 ms worst) on v0.9.0. About 23 ms of that
  is drawing and 6-7 ms playing clips (Python, ~0.6 ms per animated model; in ENGINE_NOTES.md).
  unicode3d v0.12.0 (2026-10-04), from profiling the game on an older 4-core laptop where it ran at 8-9 fps: a bot
  game at 206x49 on 4 cores / 8 threads, mid-game, 36.6 -> 24.7 ms a frame (workers sleeping between kernels, clips
  in a kernel, settled shadow casters kept, faster panel text); the laptop estimated at ~12.6 fps, to be measured.
  unicode3d v0.13.0 (2026-10-05): levels of detail at 1 pixel (half the triangles drawn) and less Python per
  object, 24.5 -> 19.5 ms a frame the same way; the laptop, with turbo on, measured 16 fps on 0.12.0 and estimated
  at ~20 on 0.13.0, measured 21 fps mid-game (48 ms). unicode3d v0.14.0 (2026-10-05): faster rasterizing and
  shading (about -3 ms on the laptop, estimated) and automatic quality (on by default here): edge smoothing off
  and 70% of the pixels measured 46 -> 34 ms on the laptop (30 fps median); to be measured in real play.
  unicode3d v0.15.0 (2026-10-05): auto steps down only below 20 fps (it stepped down within a minute at ~24);
  the 54 thin parts kept from levels of detail (below) cost about +3% (+0.6 ms here). The work
  and what is next: ~/Documents/Claude/unicode3dperformance.md.
- Visual polish: monsters read dark at whole-board zoom; mat terrain could use scattered rocks/grass props; the
  orc warlord and barbarian previews show the agents' known issues (hands off hafts, murky colours).
- Windows release (2026-10-03): `packaging/windows/` (embeddable Python as CastlePanic.exe, self-test, ConPTY smoke
  test) built by `.github/workflows/windows-release.yml` on a `v*` tag; repo github.com/arp-Trosh/castlepanic.
  0.9.0 is the playtest release. Still wanted: a playtest by a person in Windows Terminal.
- Bug hunt (2026-10-03): rules fuzz (random legal/illegal moves, garbage values: conservation, JSON round trip),
  32 whole games through the UI with random keys/clicks at 70x20-120x34 (no crash, scene matches state), a
  host+client game over localhost, malformed network messages, a pty run of `python -m castlepanic`.
- Assumptions to confirm: the monster effect-token mix (move_<colour> x2 each, draw3 x1, draw4 x1) and boss HP
  (King 2, Warlord 3, Mage 3, Healer 2).
