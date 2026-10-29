# HBM KITS19 takeover at13:55, parked on explicit14:02 reset

Source base: fb1fc79593ba9a9e4d968b80f2cd75dc44f1a056 (fresh origin/main worktree). No RTL, constraints, RC table, flow default or timing gate changed. No route/STA ECO launched during this takeover. Existing failure verdicts remain intact.

The inherited KITS19 same-pin TT probes show a real GRT-vs-routed-RCX slew gap:

| vehicle | probe GRT pins>320ps | probe routed pins>320ps | median routed/GRT ratio at violating pins | example |
|---|---:|---:|---:|---|
| RING keep A2 |0|1473|1.386|_180805_/C463.3ps vs295.6ps|
| bdring_k18 |0|7370|1.632|u_bout_bq_d/q[53] D574.6ps vs158.8ps|

Every violating pin in those probe files has a same-name GRT sample. These diagnostic counts do not replace the canonical signoff counts (RING1477TT/1157FF, bdring7496TT/6501FF). A representative RING net9653 is driven by place9654 BUFx10 with107loads. This explains why GRT-stage repair cannot close the routed-only violations; the current HBM route script reaches signoff on SPEF without a corresponding SPEF-driven data repair.

One read-only native geometry dump was launched and completed: epyc2 unit oth-ubuntu-1185111-1793307771. It records RING146441non-filler cells/160violating nets and bdring83334cells/770violating nets. Source dump_routes.py reads only the old routed ODBs. Results are epyc2:/srv/opentallas-scratch2/claude/codex-hbm-rcfix-1355/{ring,bd}_routes.json. No image was rendered/viewed before the reset; these records authorize no new physical run.

Next: render actual violating nets and review them, then build one fresh retained-route clone per affected kit for data-only repair against actual SPEF, ordinary TT setup/FF hold, incremental DRT, fresh RCX/signoff and routed LEC. Keep all source/state/cycles/pins/clock cells and routed clock wires unchanged. FLOW recommends the existing tools/s81_head/head_eco_post.tcl + head_eco_modes.py and KV eco_route.tcl session pattern: ot_mm_sync re-estimates, so read the actual SPEF AFTER sync and after any later re-estimation. Adapt the actual HBM pre-hook carefully; the HEAD runner's hard-coded bind_ff_actual/HB4 prerequisites do not directly describe these HBM kits. No FF virtual-clock rebind, global RC modification, margin relaxation or new gate is proposed.

Current source-recipe correction: K13 gq_issue1024/41033 and xp_aq1056NEQ are the stale PRE-f437 tree source, not a failure of f437090e0. Main40235e1f116 already pins the correct per-file source in recipes_other.json and recipes_b2.json; the corrected fresh fmt synth/LEC16081/16081PASS is recorded by DIE-HBM18. Focused helper gq_regen owns actual new main-source GEN/SYNTH of fmt+twoGQviews; see its explicit-reset handoff. No old AIG rerun is needed.

Division of remaining work: sibling cores_b owns QWDEC post-CTS hold, XCAL congestion and macro placements; this lane owns Ring/bdring RC repair, HNX/TKM/GQ/TOPK/selector. Inherited long-running TOPK/selector jobs were observed live and left untouched. OWNER? None.
