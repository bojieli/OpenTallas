Q3 link canonical macro placement policy

Both rightwidth A2/B2 reached zero global-route overflow and then failed
DRT-0255 at the same SRAM signal/clock pins. The hand-written placement
introduced after a missing --core-macros auto invocation bypassed the existing
canonical preferred-track snap.

The q3_link recipe now selects core_macros:auto when the CLI omits a mode.
An explicit CLI mode still wins, including off. All other307 loaded recipes
retain off by default. Site coordinates come from the existing canonical
core_macros.json table; no new placement or phase algorithm is introduced.
The existing factory applies orientation-aware snap using its actual generated
make_tracks.tcl, then writes the normal mplace table with escaped flat names.

Actual failed-kit data:298 signal/clock rectangles per g141 macro, all M4.
Actual M4 is horizontal,24nm width/pitch48nm/offset24nm; M3 is vertical,
18nm width/pitch36nm/offset9nm. There are no M5 signal rectangles, so this
R0 master requires only Y+12nm. X remains unchanged. The canonical helper
moves all4 macros from1192 off-track rectangles to0. A wrong24nm Y shift
leaves1192 off-track; passing platform defaults instead of actual tracks
would incorrectly select no movement. Existing outline/collision checks pass.
This result is master/orientation-specific; it is not a blanket SRAM shift.

Actual VIA45 has M4 landing46x24nm, M5 landing24x46nm. VIA34 has M4
landing40x24nm, M3 landing18x34nm. Corrected Y fits the24nm landing height
exactly. Landing width exceeds the24nm square pin, requiring normal
horizontal M4 extension in the72nm side access halo. At west localx24,
VIA45 lower metal spans x1..47nm, leaving25nm to the M4 OBS at72nm;
at eastx56184 it leaves49nm to OBS end56112, both >=24nm M4 spacing.
The macro PG stripes are M4 and start300nm from the west edge. Actual
rebuilt parent PDN may still block a via, so these static bounds are not an
access or PG pass.

Run check_q3_snap.py for the minimal CLI-resolution and actual-grid check.
Inputs are compact snapshots from the actual failed A2 GRT ODB/LEF/tracks.
A corrected kit must be generated through the committed recipe/factory,
rebuild floorplan and PDN, and pass fresh actual pin access before any route.
Do not move the macro in a post-CTS/GRT capsule. Preserve failed A2/B2.
Ordinary final timing/clock/DRV/DRC/PG and routed LEC remain required.
RTL and pin cycles are unchanged; no token latency charge is added.
