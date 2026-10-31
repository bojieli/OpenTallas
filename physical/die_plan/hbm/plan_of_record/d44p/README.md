# HBM plan event d44p (DIE-HBM-54, 2026-10-31)

Metadata-only event on d44o (die_plan 243ff7d018ba, core_macros 3bca79b4624e, core_conns e689ac2475d8 unchanged):
clock.tap_window.per_type_ps = {q_hub_nw: 80, q_hub_ne: 80} (COORD 14:2x APPROVED, HBM-HUBMESH-6 READY: routed a3e6s
hub mesh needed W NW 64.98 / NE 70.39 ps). window_ps 160 and seam_hold are unchanged for every other type until its own
clock form measures its needed W (OWNER 12.28b: no unmeasured tightening; SM street form needs 212-317 ps, CLKLOC-4).

die_plan.json sha256 = d8d63587cf3e (full in SHA256SUMS).  No geometry, pin, core or connection change.

G0 / G0C (tools/die_plan/check.py, --completeness) vs d44o: identical message sets (G0 2 ERROR / 964 WARN, G0C 10 ERROR /
1181 WARN, 0 new, 0 gone), reports in g0/.  Consumers: gen_phys.tap_window_ps and die_sta_related per-region per_type_ps;
core kits do not read tap_window, so every d44o core kit is valid on d44p.
