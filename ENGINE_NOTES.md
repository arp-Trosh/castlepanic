# unicode3d 0.9.0: notes from building Castle Panic

- **No model instancing.** There's no `Model.copy()`/`instance()`: putting 10 goblins on the board means loading the
  .glb 10 times (re-parsing, duplicate meshes). Games need a cheap clone that shares meshes and gives each copy its
  own clip clocks.
- **No clip crossfading.** Switching clips (Attack -> Idle) pops; games must snapshot and blend poses themselves.
- **Terminal screenshots aren't public API.** `cells_picture` lives in `benchmarks/gallery.py`, which isn't installed.
  Games want it for previews, docs and tests (castlepanic/snap.py reimplements it from `glyphs.GLYPH_SETS`).
- **Texture v orientation is undocumented** for hand-built meshes (`Mesh.uvs`): which image row v=0 lands on had to
  be found by experiment.
- **Scene-graph cost dominates busy scenes (biggest finding so far).** A board with 57 models (towers, walls,
  trees, 5 characters: 1,381 parts) renders 200x60 sextant cells in ~57-90 ms, of which ~65% is
  `Renderer._instances` -> `transforms.world_matrix` in Python: ~55 µs per part per frame (quat_to_matrix,
  normalize, np.linalg.norm and small-array numpy ops for every node; 12k quat_to_matrix calls for 5 frames).
  Board only: 17 ms. Animated glTF characters are 50-90 parts each, so 20 monsters alone cost ~60 ms/frame
  before any pixel work. Fix ideas: walk the hierarchy once into flat arrays (parent index, local pos/quat/scale)
  and compose them in one Numba kernel; or at least pure-Python float math instead of tiny numpy calls (3-5x).
  Game workaround: castlepanic/actors.py `bake()` merges a posed model into one textured mesh for static pieces.
- **merge_meshes drops textures** (it says so), so baking a textured model needed a custom merge (uvs, materials
  and texture lists concatenated, part colours as face colours). A textured merge/bake would be useful in shapes.
- **`Model.world_bounds()` is expensive per call** (~5 ms for a 60-part model): each part's `world_bounds()`
  re-walks its whole parent chain with no shared `known` cache. Calling it per frame for label placement over
  15 monsters cost 50 ms/frame. Passing one cache dict through `union_bounds`, or caching per frame, would fix it.
- **Screen text is ANSI-8 only**: `Screen.text` takes the 8 named colours, with no background colour and no
  truecolor. Card-style UIs (coloured card faces, a highlighted selection) can only use reverse/bold/dim.
- **No fonts for `text_mesh`.** It takes a bitmap font, but the only one is the 5-row partial `FONT` in
  `examples/room.py`. Banner lettering (castlepanic/fonts.py) needed two full alphabets drawn by hand. A built-in
  font (A-Z, a-z, digits, punctuation) would help, and so would a per-pixel option (each pixel its own block, for
  stone or brick lettering) next to the merged-runs extrusion.
- **No camera-space placement.** Putting lettering in front of the camera meant building the right/up/forward
  basis from `position`/`target` and calling `quat_from_matrix` (banner.py). A `Camera.basis()`, or letting an
  Object3D take the camera as `parent`, would make HUD-style 3D objects easy.
- **`DisplayControls` is all or nothing.** The game wanted only the frame rate on screen and the rest on a settings
  page, so it keeps an undrawn `DisplayControls` for the widgets and F-keys and writes the fps itself. An fps-only
  readout widget and a load/save of display settings (they are the same for every game) would be welcome.

## unicode3d 0.10.0 (moving the game onto it, 2026-10-03)

- **Built since 0.9.0 and now used:** `Model.copy()` (Library.instance), `Model.bake()` (Static), `Clip.start(fade)`
  (Actor's crossfades), `Screen.picture()` (snap.py and tools). Frame times in STATUS.md.
- **Playing clips costs ~0.6 ms per animated model per frame**, all Python (`Clip.update` -> `Animation.apply` ->
  each track's keyframe search and lerp/slerp, per node). 11 animated models: 6-7 ms of a 30 ms frame.
- **`Screen.picture()` draws box-drawing characters as empty boxes**: Pillow's default font has none, so every
  panel border and button in the screenshots is a row of tofu.
- **Built in unicode3d 0.11.0 from the notes above, and used here:** `fonts.font()`
  (fonts.py), `bitmap_mesh(blocks=True)` (the stone banner style), a Camera as a parent plus `height_at()`
  (banner.py: no basis maths), `DisplayControls(show=("fps",))` with `settings()`/`apply()` (ui.py: the
  bottom-right readout is now the clickable "F4 31/30fps"; settings.py only reads and writes the file), and
  box drawing in `Screen.picture()`. The built-in `fonts.PIXEL` isn't used (the banners keep their own styled
  fonts).

## In 0.12.0 (2026-10-04)

- Playing clips is no longer Python per track: a Clip samples all its tracks in one kernel (6-7 ms -> 0.5 ms a
  frame here). Its tracks' keyframes are read once, so give an animation a new Track rather than editing one.
- Shadows, panel text and the threading layer are faster too (see STATUS.md, Performance). On Linux, importing
  unicode3d now prefers Numba's OpenMP layer with sleeping workers; the Windows release keeps its own (vcomp140).

## After 0.11.0 (2026-10-03)

- **A one-frame flash from objects made mid-frame.** An Object3D is visible from construction at the origin, scale 1,
  no parent. The banners made one in the scene's event step, after the per-frame placement had run, so its letters
  showed for one frame at the board's centre before being moved in front of the camera. Fixed in the game
  (letters start hidden). Worth a line in the Object3D docs, or a `visible=` constructor argument.
- **Proposed widget: a docked, sliding panel** (castlepanic's multiplayer chat, `App._chat_dock` in ui.py). A tab
  in the bottom bar (label, an unread badge, ▲/▼) toggles a panel that slides up over the bottom of the 3D view
  (0.3 s, smoothstep), drawn row by row with a background fill and clipped at the bar, so the 3D view never
  resizes. The game had to write: the slide state and easing, the clipping of rows still under the bar, the
  background fill (`Screen.text(bg=)` per row), the tab's click box, and keeping clicks on the panel from reaching
  the view's camera drag. A `Drawer(Panel)` next to `DisplayControls` (`open`/`toggle()`, `draw(screen, bottom,
  left, width)`, `contains(x, y)`, a `badge`, content drawn through a callback with clipping) would cover it, and
  the same piece could serve help or log drawers.

## Precompile workers vs. launchers that take over startup (2026-10-03, v0.11.0)

`compile_kernels()` speeds up the first run with worker Pythons (`sys.executable -m unicode3d.precompile`). In a
Windows release built like Zombie Dice's (the embeddable python.exe renamed CastlePanic.exe, the game started from a
`.pth` file because a double-clicked exe gets no arguments), `sys.executable` is the game's exe, so each worker ran
the `.pth` launcher and started the game (or its self-test, which started more workers) instead of compiling: the
CI self-test hung for 15+ minutes, and a player's first start would have too. Fixed in the launcher (only a bare
start, `len(sys.orig_argv) <= 1`, is the game). Zombie Dice's launcher has the same gap but pins v0.8.3, from
before the workers: it needs the same guard when it upgrades. The engine could help either way: document it next
to `compile_kernels`, or mark the workers (e.g. `UNICODE3D_PRECOMPILE_WORKER=1` in their environment) so a launcher
can tell. With an empty cache the workers cut the first compile to 12.7 s here (12 threads).
