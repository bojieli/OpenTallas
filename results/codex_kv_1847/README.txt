KV-022 structural locality preparation, CODEX takeover 2026-10-29 18:47.
NOT ADOPTED. No new CTS/route. All inherited failures retained.

Collected inherited A/C post-CTS FF hold (ps / endpoints):
 A SD -286.68/289; A SD_v1 -379.06/853.
 C SD -251.49/1231; C SD_v1 -372.34/2015.
 D 6-tap CTS fails clock_family missing unique physical arrival on SD/SD_v1.
 D 3_place.sdc includes clk_t5, but pre_cts.tcl clears/sets latency on clk..clk_t4 only.
 This is a concrete incomplete kit edit; it may explain the query failure (not proved).

Looked at placed_sdD.png (actual source: epyc2 die-kv-38-1029/sd/varD/kv3_sys_SD).
Macro occupies 91.19%; legal logic band around S/E. Data pins E low range.
FAIL structural: rr48 raw reset at (192.0,21.7) drives FSTART face flop
(1894.6,869.0), Manhattan2549.85, 3973 captures over405. Pin-register p90172.59,
max218.0. Clock-entry-only edits cannot close that raw reset/START span.
No physical trial is allowed on this geometry until revised.

prepare_sd_locality.py consumes original event28b plan + actual placement geom.tsv.
Extracts6589 main-clk sinks from native connectivity (excludes PHY/forwarded clocks),
computes density tap sites (19 vs5/6; maximum density load931, max radius177.1).
Sets primary clk + count/START entry to East-middle at (1883.52,520), with tstart
pin(1898.656,520). First density result y432 is deliberately corrected: y432->
FSTART868.96 is437um and still violates405. Explicit root y520 gives raw-origin->
FSTART max364.096um. Explicit endpoint geometry passes outline/halo/spacing.
This is a PREPARATION, not proof that every raw/data path is closed. Other3972 paths
must be remeasured; local main/read-domain control remains a separate obligation.
SD_v1 uses SD inventory provisionally; export its own inventory before building.

No data cycles are proposed. Recompute reset release offsets and START provider
legs before source adoption. Existing collector/reset tables are stale on the new
entry geometry; MUST regenerate and strict-bind, then G0C/clock/CA+reach before
CTS. Main ECTL core mean gates continue unchanged.

Run directories (all own):
 epyc2:/srv/opentallas-scratch2/claude/codex-kv-1847/geom_sdD (actual read-only geometry)
 epyc2:/srv/opentallas-scratch2/claude/codex-kv-1847/prep (reset planner feasibility)
Local generated51MB plan stays in run-dir only, not committed. Recipe script,
small density inventory, report and picture committed. Do not adopt unbound plan.
