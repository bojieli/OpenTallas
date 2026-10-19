# Shared SRAM native rule and access method — proposal only

Owner: fresh shared Qwen/S81 method worker. ROOT approval is required before
any diagnostic design generation or execution. No production views, Liberty,
RTL, simulation, routing, PDN, gate, or native design DRC ran in this step.
GDS/CDL/manufacturing qualification is not a prerequisite for this academic
analytical macro method. None is claimed.

## Exact sources and measured checker capabilities

The two distinct conditional geometries are Qwen `5666def40` and corrected
SC2 `e91e03803`. `analysis.json` pins their full commits, actual JSON payload
hashes and all checker-source hashes. Qwen has 206 paths, 408 access vias,
44 unchanged PG rectangles, outline 52.440 × 21.144 um. SC2 has 437 paths,
870 vias, 874 retained source/terminal pads and 77 unchanged PG shapes;
outline 216.840 × 43.752 um. These families cannot inherit each other's
physical qualification. Existing 21 Qwen leaf PG_HOLD receipts concern old
masters and are not receipts for these proposed geometries.

**Correction:** the following historical installed-image claim conflated the frozen calibration ID with the current image. See [IMAGE_PROVENANCE.md](IMAGE_PROVENANCE.md) for per-host raw receipts and exact scope.

Actual installed image: `openroad/orfs:asap7lock`, image ID `af971398d91e`,
repository digest `sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`.
Binary `/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad` SHA256
`21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846`,
version `26Q3-1510-g6cb3f2b704`. Only empty-session version/help/introspection
ran, explicitly allowed by lead; see capability Tcl/logs. Global `check_drc`
is absent; actual hidden command is **`drt::check_drc`**, with native
`drt::check_drc_cmd` also present. Its source accepts `-box`, `-output_file`,
`-marker_name`. It requires a design and GCELLGRID/guide initialization.
No Tcl checker source was installed over the binary.

Exact matching upstream source is retained under `source/`, fetched read-only
from `https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD/6cb3f2b704/src/drt/src/`.
This is source evidence, not an executed geometry verdict. Native loaded-rule
objects still must be dumped by a granted coupon to verify the LEF parser's
actual data, DBU scale and rule identity. No latest/master source is used.

## Rule applicability established by source

Both models pin technology SHA256
`7694bf4f8ef2f9745e4579f454788a0cf048e8605320f32d1d83ec540ed4ca41`.
M4/M5 are 1000 DBU/um, manufacturing grid 1 nm; native tracks M4 horizontal
48 nm pitch/3 nm offset and M5 vertical 48 nm/0 offset. Both declare:

- minimum width/basic spacing 24 nm, minimum connected area 2000 nm²;
- discrete WIDTHTABLE 24/120/216/312/408 nm (M5 continues upward);
- PRL table width 0 →24 nm spacing; width 25 nm →72 nm spacing;
- EOL width 25 nm, within 40 nm, 24 nm spacing, end-to-end 40 nm;
- convex CORNERONLY 48 nm with 40 nm corner spacing and EOL keepout;
- RIGHTWAYONGRIDONLY and RECTONLY, **without EXCEPTNONCOREPINS**;
- no M4/M5 MINSTEP. A 9 nm step is not independently a MINSTEP violation.

`FlexGC_main.cpp:1949` computes RECTONLY on the connected polygon using
maximal rectangles. More than one maximal rectangle makes it a potential
violation. For each concave corner, the checker intersects a ±minimum-width
neighborhood with the full polygon and fixed polygons. If the complete
intersection is fixed, it **suppresses the marker**. Otherwise it reports
RECTONLY markers. Thus separately legal rectangular LEF primitives do not
establish a legal connected routed union; conversely all-fixed macro shapes
can be silent even for this exact nonrectangular union. `analyze.py` confirms
all 206 Qwen source joins and all 874 SC2 source/terminal joins are genuinely
nonrectangular (union area differs from bounding rectangle), not merely a
33 nm bounding-box artifact. It predicts a visible routed-metal RECTONLY
marker conditional on actual import/visibility. It does not label a macro
or route as failed before a native receipt exists.

`io.cpp:1794` imports only **ORTH** WIDTHTABLE rules into the DRT width-table
constraint; non-ORTH rules are skipped. These PDK rules do not contain ORTH.
A zero native DRC report therefore cannot prove discrete width-table legality.
The native PRL computation uses maximal rectangles and has OBS-width
configuration, so the 33 nm bounding height is not itself the measured
PRL width. Preserve the conservative 63 versus72 nm concern as HOLD until
actual union neighbors and marker geometry are observed. Manufacturing-grid
`checkMetalShape_offGrid` checks rectangle coordinates modulo manufacturing
grid, not track-center congruence. RIGHTWAYONGRIDONLY is imported separately;
no blanket failure of retained macro contacts follows from long-wire phase.

`FlexGC_init.cpp:40` assigns connected pin figures to their actual signal or
supply net, while macro OBS is owned by the instance/blockage. `io.cpp:2971`
contains a narrow conversion of a CUT OBS enclosed by one pin into that pin.
It does **not** establish a general same-net M4 routing-OBS PG exception.
PG net binding alone cannot prove a strap or via can reach through own OBS.
`pin_access` is a signal access mechanism; supply IO terms are skipped in
`FlexPA_acc_point.cpp:1568`. Native PG must be checked separately with actual
special nets, via shapes, connectivity and `check_power_grid`.

## Smallest proposed diagnostic experiment for ROOT approval

One immutable preparation, three separate processes, no synthesis or CTS.
Request unpinned ot-run admission for 1 CPU, 4 GB RAM, 2 GB disk. This is a
resource request for a few thousand shapes, not a measured runtime promise;
record peak RSS/elapsed and adjust only from real admission evidence. No
arbitrary timeout on the native task. No production helper changes.

**A: visible union checker coupon.** A 10 ×10 um diagnostic DEF/ODB has
explicit GCELLGRID and M4/M5 TRACKS. Import PDK only; emit actual REGULAR
signal dbWire segments plus dbWire patch rectangles, not FIXED/SPECIAL
shapes, and retain every native VIA45 enclosure/cut. Isolate cases at ≥1 um.
Use exact translated local pad/lead/neighbor/via coordinates selected by
stable source pin and shape role from each immutable JSON, never guessed
33 nm boxes. Include Qwen wclk (zero jog), r_ce_in (two vias) and one east
output; SC2 clk, r_ce_in and one east output. Clip exact source shapes at a join ±0.5 um halo and score only an inner
ROI so crop-edge EOL artifacts cannot masquerade as join failures. Keep
all same-net metal and the closest cross-net rectangles in that halo.

Controls: aligned 24 nm rectangular same-net join (positive); exact shifted
24+24 nm/15 nm overlap (candidate, predicted RECTONLY); that candidate
entirely FIXED (visibility negative: possible suppression, never closure);
a 23 nm cross-net spacing intrusion (causal spacing failure); disconnected
pad gap (connectivity failure); and one long-wire candidate on the old12mod48 phase (track-center
coverage probe, never mislabeled a manufacturing-grid failure). With
1000 DBU/um and 1 nm manufacturing grid, a sub-grid coordinate control is
unrepresentable; explicitly mark that control unsupported. Prefer 33 nm width
versus an allowed24 nm width as a **coverage probe**, not an expected native
width-table fail. Record all per-case markers/net/layer/boxes and shape
status. Run `drt::check_drc -output_file ...` before routing/repair, preserving
all requested shapes. No DRC-healing pass can erase the experiment.

**B: exact macro signal AP/route coupon.** After A identifies the union
behavior, instantiate one exact diagnostic abstract for each family at N,
origin (43.2,43.2) um. Preserve all contacts, full OBS, all PG rectangles and
outline; all internal analytical lead shapes must remain explicitly listed
in a companion JSON. Attach one independent external net to every signal
MTerm (206+437), with actual clocks separate, and place corresponding BTerms
outside each face with real registered-parent endpoint ownership marked
unqualified (no fake FF claim). No logic/functional claim is made by this
routing-only fixture. Parent approaches use exact native tracks; keep all
same-face nets, not only a sparse hand-picked pin. Run `pin_access` with
`-min_access_points 1`, snapshot per-pin access points, then native route
and its DRC report. Initial placement uses N only; FN/FS/S claims require
separate source-derived track-phase cases rather than reusing this receipt.
A blocked chosen terminal approach is a negative fixture; an omitted net is
an endpoint-census negative. Preserve route failures rather than dropping
problematic pins. Success qualifies external AP/route only: internal leads
hidden by macro OBS are not thereby DRC checked.

**C: real PG pin/OBS coupon**, same two masters, source pins and full OBS.
Declare distinct POWER VDD and GROUND VSS special nets and top supply BTerms;
explicitly connect every actual PG MTerm/ITerm by exact name/type, no broad
regex alias. Add real M5 landing/VIA45 at each proposed Qwen witness and
source-derived SC2 witness only where native enclosure can touch its actual
M4 PG rectangle; route to real M6/M7 orthogonal straps/source terminals.
All 44+77 PG shapes are censused, including multiple shapes sharing one
MTerm. Run PDN with failed-via report; snapshot before/after shape counts,
per-domain net graph, unbound/wrong-net ITerms, per-contact via intersections,
connected components and `check_power_grid -net VDD` / `-net VSS` without
`-dont_require_terminals`. Census zero unbound ITerms is necessary but does
not replace every-contact physical reachability. Causal controls disconnect
one PG ITerm, swap its supply net, and remove one sole landing via. Each must
fail its corresponding assertion; native connectivity silence is recorded
as an uncovered check. Keep OBS unchanged for the candidate. A diagnostic
OBS-window control may isolate the obstruction cause, but any success is
explicitly not qualification of the original master.

Record raw stdout/return codes, input SHA256, loaded rule dump, TRACKS,
transforms, complete shapes, net/MTerm/ITerm contact ledger, markers, native
ODB/DEF and one PNG per coupon. Namespaces/CLI must match captured binary.
Rule parser errors, missing GCELLGRID, absent markers on causal controls or
fixed-only visibility are METHOD INCOMPLETE, not candidate PASS. Native
RECTONLY failure of visible candidate is a concrete redesign trigger; do
not manufacture a production failure from this source prediction.

## Decision boundary and next step

ROOT can approve generation/execution of A only first, then B/C after its
visibility receipt, or approve the whole bounded diagnostic sequence. This
packet requests no production generation, adoption, native phase, clock CQ,
first-use/reset/K, timing/energy closure, or full token release claim.
All previous analytical costs, geometry holds and failed evidence remain.
