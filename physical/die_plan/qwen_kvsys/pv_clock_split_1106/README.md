# PV physical clock separation candidate
Planning/preparation only. Current POR and old kits remain unchanged.

The retained v3n FF diagnostic reproduces -360.25ps hold. Actual root-clock
connectivity contains20 hard-core clock loads,155270 soft FF loads and15
core/FF mixed roots. The worst reported scalar shift chain r20->r21 crosses
clk_t157->clk_t121; nine CTS delay buffers add~181ps before the capture tree.
Removing that prefix alone would still leave~179ps hold debt with the
unchanged140ps source window. Physical branch separation alone is not closure.

Variant A makes the20 existing core taps separate input branches. Their old
coordinates are inside the macros; a flag-only change would fail canonical
clock-entry clearance. This event explicitly relocates those new input entries
to adjacent macro-free channels with8.64um edge clearance. Estimated local
clock branch length is at most103.68um (~2.039mm total). Branch RC and actual
M5 macro-pin access through detailed M6/M7 OBS are still to measure.

Variant B also opts into the shared bounded scalar/per-bit chain affinity
(radius200um,max_group128). That source is independently owned by QC and must
be released/qualified before production use. Current density assignment splits
even compact chains across roots: d68 bit452's67 stages fit97x63um but use6roots;
a single bounded group has only79.725um maximum reach to its nearest tap.

PINCYCLES0. No data RTL/state/pins/reset/start change. All signed TT/FF core
means,833ps period,140ps type source window and actual gate budgets remain.
The20 additional clock ports and~2.039mm local branches are explicit physical
costs; this is not an ideal-latency or relaxed-window claim.

apply.py accepts only the exact reviewed type and writes a fresh private plan.
Restoring its declared clock-only changes reproduces the entire input object.
A new native header/context and strict topology bind are required before GEN.
Review images are in results/geom_review/kv_pv_clock_1106. Existing failed4_cts
and all proof/signoff data remain immutable.

The scalar worst path is specifically ot_dp_dly(W1,D23), annotated by the
captured RTL as a landing pad for as-built relative timing. Its full physical
chain spans~680x192um; whole-chain nearest-tap reach593um prevents collapse.
Only bounded contiguous subgroups may be joined; actual reach-priced u_ft
stations and different/gated clocks are not merged. Terminal q is included as
the last delay stage when its exact source/identity and physical bounds pass.
A private assignment-only canary compares953 helper off/on at unchanged
internal mode before any CTS. This is separate from A/B whole-plan variants.

## Measured successor: repaired local density plus monotone affinity

The old-grid affinity is retained as a failure control:33,144 safe clock moves
left four over-cap roots and the actual worst pd23 seam unjoined. The corrected
actual-bin density model returned159 taps but still violated its declared cap
(max1535,1114 excess sinks). The opt-in tap_capacity_repair.py adds seven legal
local sites; its sizing result166 taps/max1197/radius299.088 preserves original
cap1200/radius340/window140. A tighter200 physical target failed at a reserved
corner and was not adopted; affinity subgroup radius remains200.

An actual native166-port assignment canary now passes cap<=1200. B2 affinity
(f87028ff0c) reduces adjacent-stage crossings14532->3009 with ZERO new,
moves45687 eligible clock pins in3712 groups, max89FF/max200um. All866486 cell
master/poses and3478838 noneligible data/reset/hard/gated-clock pin records
are unchanged. Density alone puts worst pd23 r20,r21 and terminalq on clk_t128;
B2 preserves that and removes other crossings. No entire long scalar chain
is collapsed. Full audit is profile166_native_audit.json.

Actual scoped producer:

    python3 apply_density.py PLAN --core-mode internal --out PRIVATE.json

The internal variant adds6 main clock inputs (160->166). The optional early
variant also adds20 separate core-clock inputs at the reviewed channel sites.
Both emit an explicit clock ABI/map beside the private plan. All source means,
140ps window,833ps period and data/reset/START fields remain unchanged.
The type already carries a serialized collector_tree; it is preserved.
Use the released captured bound-reset export/reimport path; never silently
derive a replacement control graph from the new clock-port count.

Before fresh GEN, root/die owner must adopt the explicit parent clock table,
native header and matching canonical source/asbuilt context. Native6-port
interface changes are not covered by reusing a stale bind receipt. This is
source preparation only: the prototype ODB is an assignment component,
not a production kit, and there is no CTS/STA/route/signoff claim for it.
Keep old failed subjects immutable. Actual source/context owner is KV/wave.
