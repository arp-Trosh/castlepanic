# Castle Panic asset style guide

Every model is a Python script in `assets/src/` built with `kit.py` and exported to `castlepanic/data/models/<name>.glb`.
All of it is original: geometry from primitives, textures painted with numpy noise. Never download or copy assets.

## The look

- **1980s Dungeons & Dragons, grimdark.** Think the Monster Manual's ink-and-paint plates, Frazetta, Warhammer
  Fantasy miniatures, EverQuest-era low-poly models. Heavy, battered, dangerous. Grandiose and epic.
- **Low-poly, NOT cartoonish.** Faceted shapes, few segments (6-10 round segments), bevels on hard edges.
- **Do NOT make it look like Roblox, Minecraft or LEGO**: no cube heads, no blocky uniform proportions, no
  stud-like round eyes, no smiling faces, no candy colours, no perfectly straight symmetric parts. Use taper,
  tilt, asymmetry: a pauldron on one shoulder only, a broken tooth, a notched blade, a tilted helmet, ragged
  cloth hems (jagged extra blocks), lumpy hide (`jitter=`).
- **Silhouette first.** The game shows a monster 6-20 terminal cells tall. What reads at that size: posture
  (hunched, looming), the head shape (ears, horns, tusks, crown), the weapon (big and clear), and 2-3 strong
  colour areas. Exaggerate weapons and heads ~20-30%, like miniatures do. Fine detail turns to mush; skip it.
- **Paint like a miniature** (sound colour theory): one dominant hue, a complementary or split-complementary
  accent, neutral metals/leathers. Dark recesses, lighter raised edges (the texture helpers do grime and chips).
  Keep values contrasted: a dark-ish model on a mid-dark board needs light accents (bone, steel edges, glowing
  eyes) to pop. Desaturated earthy base colours, one saturated accent.
- **Eyes glow** on monsters (tiny emissive parts: goblins sickly yellow, orcs red, trolls pale ice-blue): the
  single most readable detail at terminal size.

## Palettes (sRGB 0..1)

| Faction | Main | Secondary | Accent | Metal |
|---|---|---|---|---|
| Goblin | sickly yellow-green skin (0.45, 0.50, 0.20) | filthy brown-red rags (0.32, 0.14, 0.08) | bone trinkets (0.74, 0.69, 0.56), yellow eyes | rusted iron |
| Orc | dark olive-grey skin (0.28, 0.34, 0.20) | blackened iron plates (0.16, 0.16, 0.17) | crimson cloth (0.45, 0.06, 0.05), red eyes | black iron, brass rivets |
| Troll | blue-grey stony hide (0.36, 0.42, 0.46) | moss (0.22, 0.30, 0.12), ochre loincloth (0.50, 0.36, 0.14) | ice-blue eyes | bone, rope |
| Goblin King | goblin palette | royal purple cloak (0.28, 0.10, 0.34) (complement of yellow-green) | tarnished gold crown, sceptre | gold |
| Orc Warlord | orc palette, bigger | black horned helm, crimson banner | bone trophies, skull | black iron |
| Troll Mage | troll palette | dark hooded robe (0.14, 0.12, 0.18) | staff with glowing emerald-teal crystal (emissive) | bone, gold |
| Healer | grey-violet hunched shaman skin (0.40, 0.38, 0.42) | leather and feathers | bone mask, glowing amber potion (emissive) | brass |
| Archer | forest-green hooded cloak (0.16, 0.26, 0.14) | brown leather (0.36, 0.22, 0.12) | pale linen, yew bow | steel arrowheads |
| Knight | worn steel plate (0.55, 0.56, 0.60) | deep blue tabard (0.10, 0.16, 0.38) | gold trim, heraldic shield | steel |
| Swordsman | oxblood gambeson (0.40, 0.10, 0.08) | kettle helm steel | buckler, leather | steel |
| Hero | bright steel with gold (0.80, 0.62, 0.22) | crimson cape (0.55, 0.06, 0.06) | white plume | steel, gold |
| Barbarian | tanned skin (0.62, 0.42, 0.30), blue woad paint | wolf fur (0.38, 0.33, 0.28) | huge double axe | iron |
| Castle | cold grey-blue stone (0.42, 0.43, 0.46) | dark slate roofs (0.17, 0.18, 0.22) | banners in arc colours | iron, old wood |

## Scale and orientation (world units = Blender units)

The board is 20 units across (castle ring radius 2.2). Models stand on Z=0 at the origin, face **-Y**, Z up.

| Model | Height | Footprint |
|---|---|---|
| goblin | 0.70 | 0.45 |
| orc | 0.95 | 0.6 |
| troll | 1.30 | 0.8 |
| bosses | their kind x 1.2 | |
| healer | 0.85 | 0.5 |
| humans (archer, swordsman, knight, hero, barbarian) | 0.90 | 0.5 |
| knight_mounted (horse + rider; the game shows it at 1.1x, not 1.5x) | ~1.4 to the helm, withers 0.75 | 1.1 long; lance tip at Y -1.34, -1.60 at the Attack's full thrust (`LANCE_TIP` in scene.py) |
| tower | 2.4 to the top of the crenellations (roof spire may go higher) | 1.1 across |
| wall | 1.0 tall, 2.2 long along X, 0.35 thick | |
| boulder | 1.0 across | |

Triangle budget: about 600-2500 per character, 300-2000 for props. Parts: under ~60 per character.

## Clips (names exact; the game plays them by name)

All characters walk IN PLACE (the game moves them across the board). Each clip keys every joint (kit.record).

**Monsters** (goblin, orc, troll, the four bosses, healer):

| Clip | Length | What |
|---|---|---|
| Idle | 2-4 s loop | breathing, slight sway; menacing, weapon ready. Frame 0 is the "rest pose" every other clip starts from |
| Fidget1 | 2-4 s | scratch head / pick teeth / sniff the air (back to rest pose at the end) |
| Fidget2 | 2-4 s | look around (head and torso turn left then right) |
| Fidget3 | 2-4 s | inspect or heft the weapon, spin it, test its edge |
| Walk | 1 s loop | a heavy stomping advance in place |
| Attack | 1-1.4 s | a big overhead smash or swing forward (-Y), returning to rest |
| Hit | 0.6-0.8 s | stumble back from a blow (the torso snaps back, a step back), recover to rest |
| Die | 1.5-2 s | collapse: knees buckle, fall back or forward; a weapon arm may drop off (scale a part to 0.001 and leave a separate "Severed" part in its place on the ground), blood (dark red flat discs scaling up on the ground). Ends lying still |
| Roar | 1.5 s | triumph: arms up, head back (when a Tower falls) |

**Defenders** (archer, swordsman, knight, hero, barbarian):

| Clip | Length | What |
|---|---|---|
| Idle | 2-4 s loop | alert stance, weapon held |
| Fidget1 | 2-4 s | shift weight, roll the shoulders / adjust the helmet |
| Fidget2 | 2-4 s | check the weapon (archer: sight along an arrow; others: look at the blade) |
| Attack | 1-1.2 s | archer: nock, draw, loose (the arrow part shoots off forward and vanishes by scaling to 0.001; the game draws its own flying arrow); others: a big forward slash or thrust |
| Cheer | 1.5 s | weapon raised high |

**Castle pieces**: tower and wall each have `Collapse` (1.5-2 s: blocks tumble and fall outward, the top
crumbles first, ending as a low rubble pile) and stand intact with no clip playing. The fortify palisade has
`Build` (0.8 s: stakes rising out of the ground).

## Joint names

Use `kit.humanoid()` for every biped (the game finds joints by these names): Root, Pelvis, Spine, Chest, Neck,
Head, Jaw, ShoulderL/R, ElbowL/R, WristL/R, HipL/R, KneeL/R, AnkleL/R. The horse (knight_mounted): HorseRoot,
Body, HorseNeck, HorseHead, Tail, LegFL/FR/BL/BR, KneeFL.., FetFL.. (the rider's Root under Body); its Walk is a gallop. Put weapons under a pivot named `Weapon`
parented to WristR (and `Shield`/`Offhand` to WristL). The archer's arrow is a pivot named `Arrow`.

## Checking your work

    blender -b --python assets/src/<name>.py
    .venv/bin/python tools/preview.py castlepanic/data/models/<name>.glb             # as the terminal shows it, 36 cells wide
    .venv/bin/python tools/preview.py castlepanic/data/models/<name>.glb --cells 14  # how small it is on the whole board
    .venv/bin/python tools/preview.py castlepanic/data/models/<name>.glb --pixels    # raw pixels, to check geometry

Look at the PNGs (assets/previews/). Check: stands on the ground (no floating, no sinking), faces the camera at
yaw 0 (`--yaw 0`), no limbs through the body, weapon clearly visible, reads as what it is at 14 cells, clips
start and end where they should.
