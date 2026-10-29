# BTAB closure continuation

Current compact candidate source: `35472bb7a` with exact interior-clock generator fix `78ffb1b489`. Shared nongated macro planner `bedf2b9d2` was merged to main `a7168d188c`; superseded prototype `92d60b092` must not be merged.

Inherited last BTAB route `2ce54bb5defe` failed TT slew268, FF hold−29.51/274, clock-pair skew206.9/185.3 and DRC1. Its intel1 source kit still contained actual 3_place/route ODBs despite the autopilot deletion note. Copied into own `codex-qc-btab-2348/censuskit`; original is unchanged.

Baseline generic flop-only tree:3442sinks,498cells,10stages, TT295.84/window67.75, FF228.55/window78.54; FAIL retained. Macro-inclusive prototype using CE6 partitioner:3446sinks,454cells,11stages, exact SRAM clock capacitance9.3458fF TT /10.3732fF FF, TT305.43/window20.14, FF232.02/window28.61; FAIL, no physical build. All322legs shortest, max leaf spread29.69, all3446pins covered exactly once. These prototype topology numbers do not qualify the independent main planner topology.

Structural candidate changes four SRAMs from one vertical stack to2x2, outline354.24x259.2→259.2x138.24 (−60.98%area). Escape-sized central30.456um and outer17.28um channels meet estimated60% track occupancy. `shrink_estimate.py` produces the geometry and actual candidate pin plot. All1318 pin names/directions and per-face ordering stay; S pitch0.24 and E pitch0.384um. Clock pin is127.452,69.12 on M5, clear of SRAM halos. Master-slice clock/reset feedthrough island moves with it. No RTL or latency cycles change.

`compact_event.py IN OUT` applies only the child outline/pins/clock-tap delta to the current QC event. On ev_qc25 this changes3types/12instances; parent partition outlines, core origins, all ports/lanes and data latencies are unchanged. Early insertion is a DECLARED250/202.5 design target pending the compact actual planned tree, never a routed number. New clock tap at792.732,449.28 versus842.424,380.214.

Trial data placement review: `results/geom_review/codex_btab_compact2x2_0014.md`. PASS-COND for one trial placement/sink census only. No CTS/route before actual placement review and macro-inclusive planned-tree PASS.

Live work: intel1 `/srv/opentallas-scratch2/claude/codex-qc-btab-compact`, tool WT `wt/codex-qc-btab-compact` on78ff; generation client intel2 PID1939267, `codex-btab-compact.gen2.otrun.log`, scope intel1 `oth-ubuntu-574314-1793258125`. Input `plan/compact.json`; G0 `g0/g0_report.json`, generated kit `kits/qfd_dv_s8x_btab_compact2x2`.

First generation stopped on faceC clock interpreted as N; exact matching master-slice clock support fixes it (18focused tests PASS including missing/wrong pin/layer/xy controls). Earlier `.lib.gz` passed to plain-text model reader was fixed by unpacking; original failed log remains. No clock/uncertainty/gate relaxed. No owner decision pending.
