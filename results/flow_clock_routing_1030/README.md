# Effective clock routing candidate — HOLD, source only

This candidate is default OFF. No kit enables it, no physical job was run,
and no existing signoff or routed result changes qualification. Root must
choose a truthful routing policy before adoption. Existing M4/M5 inputs emit
the exact legacy NDR command; this candidate does not constrain DRT to M4/M5.

The completed L0 kit declares M4/M5 in its PG geometry model, but emits no
per-net routing-layer constraint. Its config allows signals M2–M5 and has no
MIN_CLK_ROUTING_LAYER override. The planned clock nets carry the NDR, whose
M3 rule falls back to WIDTH18 nm without a spacing override; M4/M5 have
WIDTH48/SPACING48 nm. The actual long M3 pair has centres36 nm apart and an
18 nm edge gap over73.077 um of parallel overlap. Actual extracted clock-net
coupling to the partner is0.00694463 pF. These observations diagnose the
contract gap; extracted values are not model inputs in this candidate.

Local parser/help in the identical pinned OpenROAD26Q3-1510-g6cb3f2b704 was
read without loading a design: create_ndr accepts only name/width/spacing/via;
unspecified layer widths receive technology defaults. detailed_route has
global bottom/top layer arguments, without per-net/clock layer bounds. The
[pinned create_ndr parser](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/odb/src/swig/tcl/odb.tcl)
and [pinned DRT parser](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/drt/src/io/io.cpp)
corroborate this: DRT reads block SIGNAL minimum/maximum, while clock ranges
belong to global routing. Merely setting MIN_CLK=M4 cannot prohibit long M3.

The source candidate adds explicit top-level effective_clock_routing to a
master slice. Only mode=directional_envelope and layers=[M3,M4,M5] are
supported. It requires the same existing2w2s NDR on all declared layers,
explicit per-layer prebuild RC pricing that exact width/spacing, a named
prebuild RC source, measured_timing_used=false, explicit per-layer PG
obstacles (empty arrays are a deliberate declaration), and clearance_um.
No actual L0 RC inputs or authority are supplied here. Physical emission also
requires a matching explicit two-corner envelope model result. The search
records that result against the exact effective contract; changing RC inputs
invalidates it. Existing slew/window policies are retained.

The actual search model consumes max(R),max(C) across M3/M5 for its vertical
wire model, M4 RC horizontally, and the union of vertical PG obstacles. These
maxima may come from different layers and intentionally overestimate that
pair. A competing historical routing_model is refused. Trunk geometry and
model paths cannot escape the physical outline to evade PG obstructions.
This is a conservative planar RC envelope, with the existing model's limits
on vias/coupling/capacity. It is not a replacement for model qualification.
The emitter supplies the explicit NDR layers and refuses stale same-name
M4/M5-only rules instead of silently reusing them.

Post-route receipt still REQUIRED BEFORE adoption/signoff integration:

* Read actual consumed dbBlock, planned tree-net identities, NDR assignments,
  per-layer rules, detailed wire/via shapes and terminal access shapes.
* Report actual layer/length/width and parallel edge-gap distributions for
  every planned clock net, including the long-branch pair. Check actual NDR
  widths/spacing rather than assuming that assigning an NDR guarantees them.
* Distinguish bounded native M1/M2 terminal-access segments from modeled
  M3/M4/M5 trunks. Until explicit access geometry/RC bounds are approved,
  any unmodeled segment receives PENDING/FAIL, with no automatic exemption.
* Any actual trunk outside the modeled layers, width below the declared rule,
  spacing violation, missing terminal/model input, or incomplete net coverage
  fails qualification. NDR itself is not a layer-use restriction.
* Root must review the new plan/model and physical geometry before a single
  physical candidate; actual extracted timing and normal full gates follow.

If strict M4/M5 trunks are required, the current API cannot express that as
per-net NDR layer bounds. It needs a separate structural routing mechanism;
raising the signal-net minimum globally is outside this candidate.

Controls:14 focused tests PASS (per-layer model consumption, wrong/missing
RC/PG/rule/source, nonfinite RC, measured timing, blocked/out-of-outline PG,
legacy command identity, actual Tcl stale-rule refusal);2 relevant legacy
infrastructure controls PASS. No EDA validation or threshold sweep.
