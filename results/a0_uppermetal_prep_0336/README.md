# A0 uppermetal PREP — native census complete, projection unfinished at reset

PARKED on ROOT's explicit Claude reset. No new engineering or physical launch.
The M6H/M7V segment/track resource projection has NOT been constructed. This
packet finishes only the already-completed read-only native census and records
the next source/model work. No route, CTS, STA, NDR change or adoption occurred.

Canonical native inputs on intel2:
`/srv/opentallas-scratch2/claude/codex-qc-a0-0336/physical/`
`nk_pin_clock_install/clock_installed.odb` and
`nl_pin_clock_install/clock_installed.odb`.
Output/source: same run root `uppermetal/{nk,nl}`. Scheduled read-only unit
oth-ubuntu-2748119-1793379387 finished exit0. No own job remains live.

Both actual parent outlines are457.92x1157.76um. Native M6/M7 tracks are
**16nm+k*64nm**, with32nm minimum width and spacing. Use native tracks rather
than assuming another generator's32nm offset. M4/M5 tracks are12nm+k*48nm,
with24nm minimum width/spacing. All clock terminal coordinates, net names and
NDR states are captured from the actual installed ODBs, including buffer A/Y,
ICG CLK/GCLK, every sequential/macro CLK and public ck.

- NK34494clock terminals /9558nets;19hardchildren.
- NL31073clock terminals /8363nets;18hardchildren.
- Every actual clock net reports NDR NONE. The source slice also has no clock_ndr.
- All native raw hardchild routing OBS are M1..M5 (plus nonrouting implant layers),
  with actual orientations/boxes recorded, including MY children.
- Both native checkpoints have532M6 PG wire rectangles and no M7 PG wire
  rectangles in this dump. PG via objects are counted in dump.log but their
  per-layer enclosure shapes have NOT been characterized by this packet.

The existing shared core_infra clock_ndr implementation accepts M4/M5 only.
Thus M6/M7 clock NDR width/spacing/shield policy is a new explicit source/budget
choice; existing MAX_CLK_ROUTING_LAYER=M7 does not grant hidden uppermetal
capacity. Clock-cell fit and unchanged data geometry do not resolve this choice.

Next source/model task after a future authorized resume: derive compact
per-clock-net Manhattan-MST projected M6H/M7V segments from actual driver/sink
pin points and the actual compiled connectivity. Export layer, track interval,
net, native/default-or-proposed-NDR width/spacing, requested halo, via/terminal
access candidates, actual M6 PG masks, hardchild OBS and frozen channel/island
boxes. Distinguish projection from routed occupancy and flag track overlap /
access uncertainty. Keep the public E/M4 feed's declared M4/M5 planning basis
explicit; do not silently relabel its cost or add it twice.

The parent-view contract still requires an ACTUAL selected abstract audit. Plan45
has64type-level A0 hard-core entries but no explicit obs_max, LEF or LIB fields;
missing values do not prove an OBS5 ceiling or free M6/M7. ROOT supplied these
current capsules immediately before reset; they were NOT inspected here:

- intel2 `codex-qc-count-wave-1030/gen_views_fixed/cbf_q01/cbf_q01` (NK)
- intel2 `codex-qc-count-wave-1030/gen_nl_decl/cbx_q10__cl89936551/cbx_q10__cl89936551`
  (NL declaration candidate), or original `gen/cbx_q10__cl89936551/...`

Read config.mk ADDITIONAL_LEFS, native_bb.json and selected closure kit_rtl.json.
ROOT warns these may expand full native A0 source rather than use an opaque
closed A0 view; do not turn their declaration/source count evidence into a
hardview closure claim. ROOT/FLOW must decide parent OBS/reserved capacity and
die FT M6/M7 overflight compatibility before any A0 GRT/STA.
