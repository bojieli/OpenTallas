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

Legacy guard correction: oldB cts_B.log readWC(modeSS)/BC(modeFF), despite its
TCsetup config. The inherited -188.18ps setup label was SS, never TT closure.
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
