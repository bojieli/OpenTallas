# Shared Qwen/SC2 new-master coordinate model after Stage A failure

MODEL ONLY. One concrete choice is independently enumerated for both families;
no new geometry view, LEF, Liberty, GDS, coupon, OpenROAD or B/C run is produced.
The original 2c2d5e683 failure, original masters and all raw markers stay immutable.
ROOT must review this model before authorizing a representative visible-wire coupon.

The new analytical core offset is old X, **Y=39 nm**. Every original logical
source terminal/contact and its core/bit attachment moves +39 nm Y together.
This is a changed physical master: its internal transistor/contact row placement
is conditional on the original analytical core, not fabricated or extracted.
Existing native M4 leads and complete VIA45 stacks move +48 nm Y. Thus the
old contact center12mod48 plus39 and old lead center3mod48 plus48 coincide
at3mod48; M5 centers remain0mod48. No pin name, net or bit is relabeled. The
actual source pad and the whole core move, rather than pretending that a changed
lead can remain attached to an unchanged contact. Original SC2 external pads
also move+39; Qwen external terminals already at native lead phase move+48.

A simple -9 nm whole-core move was rejected because the original core starts
at Y=0. The selected+39 nm core fits both complete inventories and avoids the
negative bottom edge. Analytical core width/height bounds are conservatively
rounded upward to the1 nm manufacturing grid; this is a reservation, not
a transistor layout. First/last signal terminals, every rectangle, complete
via metal/cut and core/OBS/PG bounding boxes are in model.json. Heights grow
48 nm, keeping original outline phase24mod48; widths stay unchanged.

| Independent inventory | Qwen5666 | SC2e91 |
| --- | ---: | ---: |
| Signals / complete VIA45s | 206 / 408 | 437 / 870 |
| Actual PG contacts, none omitted | 44 | 77 |
| Outline µm | 52.440 × 21.192 | 216.840 × 43.800 |
| Added area µm² per master | 2.51712 | 10.40832 |
| W/E density pins/µm | 4.860 / 4.860 | 5.000 / 4.977 |
| Nominal 43.2-lattice reservation µm | 86.4 × 43.2 | 259.2 × 86.4 |
| Min parallel M4/M5 gap nm | 50 / 72 | 50 / 72 |

These are coordinate checks, not native qualification. New signal same-layer
connected components are independently unioned by rectangle overlap and exact
union area; every component is rectangular,24 nm wide, ≥2000 nm², native-phase
and outline-contained. All existing native vias retain exact24 nm cuts,
46×24 nm M4 and24×46 nm M5 enclosures. Every same/cross-net signal, via metal,
and PG neighbor participates in the finite24 nm and wide-metal72 nm parallel
spacing inventory. Both checks have zero violations. Native PRL/EOL/convex
corner applicability, via-cut/neighbor EOL and density/fill remain open: these
simple distance checks do not replace the real checker. The original old-union
analysis finds206 Qwen /872 SC2 nonrectangular connected metal components.
The earlier874 count named SC2 endpoint joins separately; two zero-jog nets
connect their source and external contacts into one component each.

## Every PG contact is redesigned explicitly

The actual tech declares M4 widths24,120,216,312,408 nm. Both old inventories
have96 nm PG rails, absent from that routing table. This is not a measured
native PG failure: applicability to fixed macro PG pins/rails remains unproved.
This conservative new routing-visible PG proposal uses120 nm. This model retains
all44/77 original identities and X spans and makes each rail120 nm wide,
center+51 nm Y (phase3mod48); lower edge+39 and upper edge+63 nm. The core
moves+39, so internal PG rows/straps must attach12 nm above their translated
old positions. This is a real conditional internal PG attachment change,
explicitly recorded per contact; it is not proof of transistor/contact layout
or electrical connectivity. Total PG metal becomes165.74976/1603.3248 µm².
Each old→new SIGNAL and PG rectangle, via, terminal and attachment obligation
is in model.json. No PG contacts are dropped, hidden by OBS or declared fed.

PG sheet resistance is recomputed per rail from the pinned24 nm RC scaled
by24/120; a width-linear PG capacitance is listed only as an analytical
conditional estimate. Actual contact R, coupling C, supply return, IR/EM,
internal straps and all121 contact accesses remain NULL pending PG design.
PG is supply metal and is not falsely charged as toggling signal activity.

## Recomputed access cost and reservations

For every pin, union metal area/24 nm gives metal length separately on M4/M5,
including the actual via enclosures. Wire C uses pinned0.178475/0.164264 fF/µm;
wire R uses0.0180365/0.0189935 kΩ/µm plus0.0118 kΩ per complete via. The
per-pin R(C+load) bound is recomputed across loads0,0.72,2.88,11.52,23.04,
46.08 fF. This wire-only bound excludes the conditional internal driver/core.
Recomputed total lead C is545.66542164/2424.095119446 fF. At TT0.7 V, complete
boundary clock cap is22.381158938/13.1623094 fF and clock supply energy is
10.966767880/6.449531606 fJ. All-nonclock-leads full-toggle plus complete clock
is276.534940604/1192.386050529 fJ. This is a simultaneous full-toggle access
bound, not an inherited read/write functional activity measurement. Every
corner is recomputed separately in model.json using the pinned analytical
original intrinsic clock cap; core dynamic/leakage and transistor placement
remain conditional and are not claimed characterized. Native minimum CQ,
maximum CQ, setup/hold, clock propagation and complete extracted RC are NULL.
No old positive minimum-CQ, timing closure or driver validity is inherited.

The26-bank Qwen candidate adds65.44512 µm² at this master-only level; all
other bank/soft/PG/channel/parent costs remain those independent open models.
The nominal lattice reservations do not change after+48 nm height. They do
not prove actual parent fit, channels or the prescribed connected cell band.
OBS reservations translate+39 nm with the complete core; they are recorded
as reservations, not generated router obstructions. Existing own-pin/PG/OBS
access issues are explicit HOLD; no signal/PG geometry is erased to hide them.
All44/77 PG contacts intersect their own current M4 OBS reservations;
this explicit AP/PG HOLD is enumerated by contact ID. Every translated OBS
is outline-contained and all complete via-cut pairs pass the conservative
34 nm box spacing test. External-face rectangle containment and density
do not establish unobstructed parent approach or an AP.
Actual AP/OBS and keepout design follows only a new ROOT grant.

At R0, required local M4/M5 phases are Y3/X0. MY needsY3/X24; MX needsY21/X0;
R180 needsY21/X24. The selected new master permits **R0/N only**, at originX/Y=0mod48,
compatible with43.2 µm placement origins (43200nm=0mod48). Old LEF SYMMETRY
is not inherited. FN/MY, FS/MX and S/R180 are REFUSED on those origins with
unchanged global M4Y3/M5X0 tracks: their required phases differ. A parent
requiring any mirror must obtain a separately priced geometry/track model.
Parent-origin translation adds to the listed local phases mod48; it is not
permission to alter parent routing tracks without review. Reusing R0 tracks
for mirrored masters is refused. This conditional transform does not qualify
native transistor grid/orientation legality of the unavailable analytical core.

## Exact source semantics and reproducibility

input/qwen_original.v is byte-preserved cdf9e0528 actual32x64 source, SHA
checked against5666 provenance. Separate posedge wclk masked writes and
posedge rclk enabled registered reads stay unchanged; no reset is added.
Same-address simultaneous cross-clock operation remains forbidden by the
existing contract; no OLD promise is invented. input/sc2_original.v is the
byte-preserved19ccd29b9 actual512x128 repair-aware source. Its one posedge clk
reads before blocking word_write, preserving its original same-edge OLD order,
mask, row/column repair, OT_MEM_NO_INIT and fault-model semantics. No reset,
new clock, extra state/cycle, initialization guarantee or first-use claim is
introduced. No source RTL is changed. Memory lifetime/K/native phase/source
clock ownership and token claims remain open.

Run `python3 model.py` to reproduce model.json and compare summary.json.
Finite local coordinate/RC work took~2.5 s; no simulator/synthesis/EDA ran.
Six causal model refusals cover old nonrectangular join, -9 nm negative core,
old96 nm routing-width-table absence (not native PG failure), pin-only/core mismatch, wrong mirror phase and fixed-pin
visibility hiding the same nonrectangular union. They are geometry/model
checks, not substitutes for actual native causal controls. Inputs, model and
script hashes are in SHA256.json. Initial missing durable V-path lookup was
read-only and resolved by retrieving exact Git objects into this own sparse
worktree; no other agent worktree was modified.

The current coupon host image digest is16470cea… and binary21eda99e…,
version26Q3-1510-g6cb3f2b704. af971398… is the FROZEN analytical calibration
image identity, never a claim about the current executable. The exact tech
hash7694bf4f… and input hashes are recorded; native checker table-binding
coverage gap and true fixed-BPin suppression from aeeb/2c2d remain unwaived.
