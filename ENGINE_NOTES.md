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
