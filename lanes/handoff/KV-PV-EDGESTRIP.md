# KV-PV-EDGESTRIP handoff (2026-11-24 01:35 PST)
JOB: pv face-strip taps over the cap (kv3_pv_v12e/v7e/v2ne/v6n/v5ne/v1n). ROW-REBASED posted 01:30.
ROW: epyc10 /srv/opentallas-scratch2/claude/kv-pv-edgestrip/row/ROWS_KV-PV-EDGESTRIP.py aff53806cf56, ES_RESETS=resel. On A5r 41044638cda3 -> resel/final.json 929ffad13f9b.
CAUSES: v12e/v7e = reach_fix_sinks duplicated about 7x (reach_fix.py density loop appends every round, no dedup; FLOW should fix the generator). v2ne/v5ne = stale clock keepouts (copies of landing bands that have moved). v6n and v1n are already under 1200 on the plan model.
GATES: PRE matches base (23 RSTREACH, diff 0). TAPOFF PASS. G0 has the same 6 inherited errors; the new warns are collector_reach info only. Strict scoped bind (base/anchor/resel) all stop at die-level R8_STALE head / pvw_0 col 2 join depth, owned by KV-ALLFIX. Per-type strict 0 is not shown yet: re-run row/sbk.sh PLAN TAG on epyc10 after KV-ALLFIX fixes the R8 table.
PLACED CENSUS (posted 01:1x): K2 v6n placed 139670 regs vs 57997 plan; 42/91 taps over 1000, worst 15018 (core-row gaps, pad-delay chains). All kitted pv types are x1.3-3.0 over plan. They need a placed-census tap row after DLYAP/WIDERAM place. Table: epyc10 kv-pv-edgestrip/row/v6n.txt.
Own tree fork: epyc10 kv-pv-edgestrip/tree (50 GB). Delete it with ot-delete when no longer needed.
