# Current A0 milestone: actual-pin clock geometry installed

The current candidates are NK **9,521** and NL **8,328** clock cells, installed
in fresh widened PLACE checkpoints. Current reports and source are under
`actual_pin_clock/`. Earlier reports below are historical experiments. In
particular, all body-centred clock-leaf predictions and the 9,557/8,108 physical
prototypes are superseded by the actual OpenDB clock-ITerm candidate here.

| Result | NK | NL |
|---|---:|---:|
| Related-pair TT/FF maximum ps | 77.674 / 60.532 | 74.863 / 55.681 |
| Maximum TT/FF slew ps | 51.329 / 47.664 | 54.026 / 52.961 |
| Weighted absolute insertion TT/FF ps | 1052.686 / 823.265 | 937.164 / 733.122 |
| Full effective insertion TT ps | 1004.176..1097.403 | 878.191..982.717 |
| Full effective insertion FF ps | 784.666..873.689 | 700.428..780.184 |
| Actual FF reach maximum um | 404.08 | 403.00 |
| Direct macro-interface reach maximum um | 340.944 | 268.264 |
| Public signal pins restored exactly | 2,584 | 1,042 |

These are pure joint-NLDM geometry predictions, not measured timing. Related
pairs and electrical slew pass 80ps. Every leaf uses its actual clock ITerm
coordinate; buffer interconnect retains the compiler cell-centre convention.
Both models assume 20ps external clock slew. Explicit passive entry wire and
four-buffer public E/M4 feed are included once. The public pin centres/layers
match plan45; 192x24nm M4 boxes touch the legal edge. Leaf macro views and actual
signed internal insertion are retained. No scalar stage-delay surrogate is used.

The final ODBs are on intel2 under
`/srv/opentallas-scratch2/claude/codex-qc-a0-0336/physical/`:
`nk_pin_clock_install/clock_installed.odb` and
`nl_pin_clock_install/clock_installed.odb`. Installation guards confirm all
planned buffer masters and direct clock parents, all actual row/site/body
footprints, zero installed-body displacement and every original instance
master/bbox/orientation unchanged. Native PG and check_placement pass. Original
functional ICGs remain 36/34. Exact data graph and clock-gate ancestry comparisons
pass; a real wrong-domain ODB mutant is rejected despite unchanged sink totals.
This is structural netlist proof, not a fresh RTL simulation claim.

NK clock-first placement requested 8um displacement but the DPL request was soft:
its actual maximum axis displacement was 61.02um. Three residual overlaps were
repaired locally, maximum 65.178um. Actual reach and complete final geometry were
then rechecked. Direct macro-interface reach covers actual macro pins; FF reach
is the separate standard-cell graph scope, not hidden flattened macro FF reach.

The current frame file records old per-core NK insertion 665.8/576.5ps and NL
692.6/601.9ps separately from these absolute new models. Wrapper 250/202.5ps is
not old core insertion. Exact safe-tree binding and actual input slew/pricing
remain with the die owner; no SDC adoption or compensation has occurred.

Documentary fields inherited in the unfrozen slice still mention centre-entry,
TritonCTS fallback and an M9-to-M5 island stack. Those fields did not drive the
actual explicit core_tree installation and are not a frozen routing budget.
Normalize them in the root-owned adoption event; qualified source bytes remain
preserved here. The report helper also retains an old UNBALANCED scope label;
current pass/fail is stated by the actual related-pair and compiler outputs.

Shared source dependencies are FLOW electrical compiler dd97876d3, deferred-set
performance fix f3f3e2d60, and private late-hook row-cache e6a71788c. The latter
was replayed against every completed NL placement with zero mismatches and used
only for these guarded candidate installations. Source snapshots here are
results-local opt-in helpers; this branch does not adopt shared defaults.

**GRT/STA remain held** for ROOT/FLOW layer/OBS and die clock-frame review.
M7 vertical/M6 horizontal access is a proposed budget: actual child clock pins
are interior M5, with child OBS through M5. No routed capacity, setup/hold,
SIGNED view, or project closure is claimed. Source RTL/data/reset cycles added:0.
Rendered actual-pin candidates were personally viewed; see
`../geom_review/a0_actual_clock_pins_0336.md`.

---

# A0 internal clock corridor rebuild and electrical planning

Both fresh placement prototypes passed: NL on intel2 unit99116, NK on epyc2
unit2816354. Their wholecore pins, outline, source RTL and child macro masters/
Liberty views are unchanged. Second/third rawleaf columns move+2.16/+4.32um.
NL actualr2r maximum403.0um, NK401.92um; neither has a capture beyond405um.
Pin-register p90 is8.62/8.28um; no standard cells lie on macros.
No CTS, signal GRT, detailed route, SIGNED view or adoption is claimed.

The actual rowcut uses4.32um macro halos, while the old clock planner used5.8um.
It erased the legal clock column between two macros and sent two pipeline FFs
13.6um apart to clock leaves~80um away. Existing narrow-strip fill71.3% left
no safe capacity for paired clock leaves. The widened legal row strip instead
reserves SITE-ALIGNED1.944um clock micro-islands on3of5 physical0.27umrows, leaving
fullwidth rows for wider data/reset FFs. Clock body+shield crosssection fits the
column. Clock occupancy estimate~52%, data~49%; actual clock-cell capacity is
still pending the final tree. Vertical clock uses preferredM7, transverseM6;
both lie within the existing parent MAX_CLK_ROUTING_LAYER=M7. Current die-over-
core FT/OBS budget adoption check remains with the die owner.

V1 failed pre-GPL anchor row validity:1375 old homes entered translated macro
row halos. Its own container was stopped and logs/ODB preserved. Exact actual
row/master-footprint projection corrected all homes: NL13324homes/max4.458um
movement, NK12814/max4.438um; zero row-footprint/reserved-island errors. V2 is
fresh floorplan/place, with exact unchanged synthesis reused; old placement
was never reused. NK floorplan admission raced a client cancellation: one
resubmission exited125 on the existing container name, so no second physical
run occurred. Canonical per-stage ORFS logs and completed floorplan survived;
the affected launcher log/collision are retained.

AUTO-GEOM failures remain immutable. Aspect/partialface are inherited from the
existing parent outline/interface; clock reach is pre-CTS. Data demand warnings
use9um/7.5um sliding windows. Explicit actual continuous corridors are73.032um
(NL) or79.32um(NK) vertical and20.112um horizontal. A32um data corridor and16um
horizontal corridor price the SAME reported equivalent demand below0.6, including
an8track clock reserve: worstNL0.552, worstNK0.549. The capacity estimate/render
is a planning result, not a GRT PASS; real routing and actual routed reach/timing
remain required. Actual placement, anchor and corridor images were viewed.

Legacy diagnostic correction: oldB cts_B.log prints WC(modeSS)/BC(modeFF),
but that is hardcoded scene/mode label text. Both retained and current helper
honor OT_MM_SETUP_CORNER=tc, and oldB config requests tc/BC. It does NOT prove
canonical old CTS used SS libraries. The -188.18ps earlier diagnostic and the
explicit TT-only diagnostic -65.68ps setup differ in probe library choice;
canonical CTS setup corner must be identified from actual loaded libraries.
Explicit TT-only diagnostic on the old checkpoint is stillFAIL(-65.68ps setup),
worst rawleaf5->parent fault_q[4]. Old FFhold remainsFAIL(-129.25), FF->rawleaf.
The opposite-direction failures share the macro/parent clock imbalance. Refresh
CURRENT hold-script tools before any new CTS; never copy the legacy guard.

The terminal-stage padding experiment is rejected:125004clocknodes and still
173.28psTT/139.35psFF global effective window. It was model-only, no build.
Natural local clock trees reduce node count:7711nodes,36functional gates and
all15379NKclock sinks retained,419spatial subregions with nominal internal
leafmean windows<=19.46psTT/14.28psFF. Bottom-up jointTT/FF branch balancing adds
only1698 designed shared-trunk cells(total9409). Full re-prediction gives
106.31psTT/83.19psFF effective global window; globalmax-min is information.
Exact physical data-connectivity pairing(49845pairs,0missing clocks) gives
FF PASS worst61.74ps, TT FAIL93.73ps/182pairs, all into the node macro. Ordinary
FF->FF is<=51.15psTT/46.65psFF. A second model-only fork-balancing pass is in
progress; no per-pair useful-skew target or clock/uncertainty relaxation is used.

Live model and all artifacts: intel2:/srv/opentallas-scratch2/claude/
codex-qc-a0-0336. Parent/child sources remain opt-in and unadopted. No new owner
question. Every RTL-cycle contribution is0; any physical clock-latency/frame or
crossing change must enter the single QC plan event before adoption.


Continuation: shorter clock structure and finite row packing
--------------------------------------------------------
R2 finishes nominal related-pair PASS77.49TT/58.21FF but needs1633.21TT/1242.67FF weighted insertion and has1010exact coincident clock sites. It is NOT physical-ready. The long insertion is caused partly by an8ps per-fork joint-corner optimization goal. Q20 changes that planning goal to20ps while keeping the actual80ps related-pair gate:8670nodes,959designed shared-trunk cells, weighted761.268TT/585.064FF, nominal PASS74.276TT/74.828FF over49845actualdata pairs/0missing. No useful-skew pair target or RTL/data-cycle change.

Packing around already placed stdcells FAILS149.51TT/127.00FF because the narrow right boundary is occupied; leaf-first alone cannot fix it. A clock-first alternative packs all8670on exact actual rows around36fixed functionalICGs:0clock/ICG overlaps, maxmove1.678um, mean0.1205um. Re-predict yields nominal PASS75.306TT/74.833FF. The rendered clock placement was personally VIEWED; PASS-COND for bounded standard-cell re-DPL only. Full tree segments are schematic, not physical routed legs. Macro bodies/outline/pins remain unchanged. Parent approved explicit bounded clock-body reservation followed by bounded movable stdcell DPL, exact datareach/face re-census, correlated model/render before GRT.

Actual k46 tree Ainv+B latency sensitivity report is conservative at containing-partition granularity:16types/192partitions/768cores,5985selected tap pairs,202missing endpoint geometries conservatively expanded. It proves the1.383ns TT R2 advance cannot generally be removed below current local LCAs. Absolute landed phase margins are NOT gates: forwarded phase offsets, exact per-core bindings and master calibration remain outstanding. Q20 is a shorter replacement and must re-price its final frame before clock implementation.
