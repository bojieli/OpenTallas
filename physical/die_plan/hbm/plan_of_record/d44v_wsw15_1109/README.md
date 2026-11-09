# d44v_wsw15_1109: d44v_restore_1109 + event wsw15_1109

Built by DIE-HBM-97 on 2026-11-09. The event wsw15_1109 was first built as plan d9301d138794a71a on d44v_corepins_1109 (3742832d6eb33412) and accepted by COORD. Hold q_hub_ne/nw until wsw_H11 is signed off. Here it is rebased onto d44v_restore_1109 (27e46e2d84777acf) with tools/rebase3.py, a 3-way field rebase that applies (wsw15 - corepins) onto restore. 22 leaf changes applied; the only conflict was the top-level note, which was merged by appending.

Plan `die_plan.json.gz` = sha256 4a66235b19a1bb7e (uncompressed, json indent 1).

Changes, all in q_hub_ne and q_hub_nw:
- u_wbk_Q__q0__sw and u_wbk_Q__q1__sw: outline 233.28x544.32, origins 1002.24 / 5253.12, pins_file cores/ot_wbq_sw__233.28x544.32__wsw15.json (sha 4509fec2).
- u_xl_Q_aqhi: origin (5132.16, 2868.48), on the 8.64 lattice.
- q_hub_nw ft_slot L7001x1: regs[3] = [980.64, 3538.08] and regs[4] = [980.64, 3166.56], moved out of the grown q0 sw.

Sidecars: none changed, so clock_entries.json.gz, core_macros.json and the other cores/ come from d44v_restore_1109 (and below). This dir adds only the wsw15 table.

Gate: check.py --completeness --plan-geom report (intel1). Base d44v_restore_1109: 984 ERRORs. New: 984 ERRORs. Both are G0C FAIL with 64 pending-view. ERROR messages: new-only 0, gone 0.

Re-keyed types: q_hub_ne and q_hub_nw only, after wsw_H11 is signed off.
