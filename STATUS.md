# Status (2026-10-03)

Playable end to end: `python -m castlepanic` (menu -> single player 1-6 / host / join -> game -> game over).

## Done
- **Rules** (`rules.py`): the full standard game + solo variant; JSON state for the network. Tests: `tests/test_rules.py`
  (incl. 300 all-bot games checking cards/tokens are conserved), `tests/test_net.py` (lobby, start, chat, remote
  turns, out-of-turn errors, disconnect -> bot).
- **Bots** (`bots.py`): one-move lookahead for hits/slays, rules of thumb for the rest. Win rate ~16% overall
  (solo ~36%, 6 players ~2%): Castle Panic with these token counts is hard; room to improve (planning across
  the team, smarter trades).
- **3D** (`scene.py`, `actors.py`, `fx.py`, `board.py`): painted mat + table, 36 forest props, 6 towers / walls /
  palisades, sentries fidgeting on the walls, every rules event animated (spawns walk in, defenders loose arrows or
  charge out, Hit/Die clips with blood, walls/towers collapse with dust and debris, the boulder rolls through and
  crushes, tar, drive back, build, heal sparkles, victory/defeat). Camera eases to the action; arrows/+/-/R steer.
  Static pieces are baked into a few meshes each (unicode3d's `Model.bake`) for speed; every piece is a
  `Model.copy()` of a model loaded once, and clips crossfade with `Clip.start(fade)`.
- **UI** (`ui.py`): menu over a live board, lobby with seats/bots/chat, game screen (status, 3D view, players with
  open hands, log, hand as card boxes, prompts, letter/click targeting, wall numbers, trade flow, help overlay H).
- **Network** (`session.py`, `net.py`): host/join, port 5555, lobby, bots fill seats, chat strip, a leaver becomes a bot.
- **Banners** (`banner.py`, `fonts.py`): 3D lettering in front of the camera. A new siege opens with three gold
  lines, the war horn (`start`), "tHe mOnsTeRs aRe CoMing!" in castle blocks, then the first six Monsters march
  in together. That announcement comes before the first new Monsters of every turn, and "Your turn. Defend the
  Castle!" at the start of yours. Space/Enter/Esc hurries a banner away.
- **On the board**: ring names (Arc/Kni/Swo) on the three lines where the colours change, placed so they never
  overlap each other or a Monster's label (a line shows whole or not at all; zoomed far out, only the nearest line).
  Monster tags (GK OW TM HL TR OR GO) before the health pips (`SHOW_TAGS` in ui.py to drop them). The camera eases
  back to the whole board 1 s after the action ends. An END TURN button in the side panel.
- **Settings** (`settings.py`): characters, colours, frame rate, shadows, reflections on the menu's Settings
  screen, saved to ~/.config/castlepanic/settings.json (command-line flags win); F2-F6 still work. The bottom bar
  shows only the frame rate.
- **Sound** (`sound.py`): 33 synthesized sounds (numpy + numba filters), played via winsound / pw-play / paplay /
  aplay / afplay; nothing to install. `python -m castlepanic.sound` plays them all.
- **Assets**: 21 models by Blender scripts in `assets/src/` (kit + STYLE.md), exported to `castlepanic/data/models/`.
  Tools: `tools/preview.py` (terminal-accurate contact sheets), `tools/scene_game.py` (bot game through the scene,
  off-screen), `tools/ui_test.py` (scripted UI run with screenshots).

## Next
- Performance (unicode3d v0.10.0, 2026-10-03): a 5-turn solo game at 170x50 (8 Monsters, ~640 parts) takes
  30 ms a frame (median; 35 ms p90, 60 ms worst), against 43 ms (637 ms worst) on v0.9.0. About 23 ms of that
  is drawing and 6-7 ms playing clips (Python, ~0.6 ms per animated model; in ENGINE_NOTES.md).
- Visual polish: monsters read dark at whole-board zoom; mat terrain could use scattered rocks/grass props; the
  orc warlord and barbarian previews show the agents' known issues (hands off hafts, murky colours).
- Windows packaging (zombieDice's PyInstaller workflow) and a real-terminal playtest on Windows Terminal.
- Assumptions to confirm: the monster effect-token mix (move_<colour> x2 each, draw3 x1, draw4 x1) and boss HP
  (King 2, Warlord 3, Mage 3, Healer 2).
