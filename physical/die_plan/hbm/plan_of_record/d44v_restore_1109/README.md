# d44v_restore_1109: HBM final plan d44v_corepins_1109 + event restore_1109

Built by DIE-HBM-97/RESTORE on 2026-11-09 with tools/restore_1109.py (copied here). The input was d44v_corepins_1109/die_plan.json.gz (sha256 3742832d6eb33412), with the final's own sidecars (clock_entries, core_macros, core_conns, cores/ of the materialized plan_final3 dir). The final was built on plan_final3 and so lost signed hard-core forms that the d44v lineage (and d44v_gqi) carries. This event replays the original d44v events in their original order, each with its own script or logic. No gz was hand-merged.

Plan `die_plan.json.gz` = sha256 27e46e2d84777acf (uncompressed, json indent 1 as the final). 4 of the 5 events are replayed. opsarest_c2_1107 is NOT replayed: its own script fails closed on the final (see below).

| step | event (d44v commit) | module | instances | what changes | new table |
|---|---|---|---|---|---|
| 1 | part60 (7de1e0f41b) | ot_hgi_coll_inj_idx_join_rg | 4 (q_hub_nw/ne u_cij_Q__q{0,1}) | 4 pins_file | cores/..centry__r1drop.json (03f1eb6f), 4761 -> 4730 pins |
| 2 | part61 (bbda1ab30f) | ot_svgr_bk | 16 (q_hub_nw/ne u_svg_Q{0..3}__b{0,1}) | 16 origin/outline/pins_file/note back to pre-part-53 (302.4 -> 259.2 x 207.36), 16 clock taps, 16 clock_entries stream_clk 22.008 -> 21.72, core_macros ot_svgr_bk entry back to pre-part-53; part 53 station sites stay | cores/ot_svgr_bk__259.2x207.36__d44v_p61.json (8ba15281) + corelat/cycles_svgr_bk_vB_1107.tsv |
| 3 | expx328_1107 (ccbad2a1c5) | ot_hbm_su_pg_lane_exp_x_core | 60 grown 319.68 -> 328.32 x 207.36 (obs M6) | 12 exp_x + 36 ot_hbm_su_pg_sfu_s_core shift <= 8.64 um (the same 48 moves as d44v), 96 clock taps, 60 clock_entries -> (164.16, 103.68), core_macros exp_x entry = d44v's; ft_nudge re-sited the same 6 bit_sites slots + 2 regs_explicit slots as d44v (ft_s0_resite --medoid-fix on the 6); 2 internal_stations chains (q_su01__physical_v1 bus:L5090_o, bus:L5091_o, 1 reg each) re-sited off the grown pair (final-only stations) | cores/ot_hbm_su_pg_lane_exp_x_core__328.32x207.36__d44v_expx328.json (ec6b144f) |
| 4 | qcore267_1107 (0cf1ab2aa7) | ot_hbm_su_static_qcore_r13 | 2 (q_hub_ne/nw u_sucore_Q__q0) | 2 pins_file | cores/..centry__s267drop.json (330ffe42), 1473 -> 1472 pins |
| 5 | opsarest_c2_1107 (834d940a5e) | ot_hgi_sfu_opsa_rest | 2 (q_b113(+__physical_v1) u_sfucore_Q_opstore_a__r) | NOT REPLAYED, plan unchanged | - |

How each was replayed:
- part60, qcore267: the new table is the final's old table minus the dropped pins, checked byte-equal to d44v/cores; the instances are repointed as mk_p60.py / drop_face_shell_pins.py did.
- part61: mk_p61.py logic. Rows and taps come from d44v die_plan at 01a61d4b8ca^1 (pre-part-53). The table is d44v's p61 table (pre-p35 bytes). On the final, only the ot_svgr_bk entry of core_macros goes back (mk_p61 replaced the whole file after asserting only svgr_bk differed).
- expx328: results/die_hbm_1107/expx328/mk_expx328.py run unchanged, then the replay.sh post steps (ft_nudge, ft_reach_fix, ft_s0_resite --medoid-fix). The generated table is byte-equal to d44v's. The moves and ft_nudge slots equal d44v's expx328_1107_event / ledger. ft_nudge on the base alone moves nothing.
- Kept as in the final: q_su00/q_su10 (+__physical_v1) u_su_Q{0,1}_lane_exp0__l stays module exp_x, 319.68 x 207.36, oneclk table (EXP0-KIND1-1108). It is held out of the row solver as a fixed item, so it is neither grown nor moved; its __s partner does not abut it. Its clock entry row still names full_x, as in the final.
- opsarest_c2: results/die_hbm_1107/opsarest_c2/mk_opsarest_c2.py, run unchanged, stops at its own assert that every moved reg-to-reg link is <= 452.5 um (measured one-cycle reach at 833 ps). The cause is that the final carries restjC_1108: u_sfucore_Q_ctl__rest is 267.84 x 267.84 at (587.52, 1105.92) MY, where d44v has 427.68 x 453.6 at (509.76, 1010.88). At the d44v origin (1131.84, 959.04), ctl_rest <-> rest links reach 502-546 um. opsarest_sweep2.py over the script's own placement space (R0/MX/MY/R180 x the 4.32 lattice of the old slot) gives at best 489.8 um (MX 1080.00, 963.36: meta_78 -> ctl_rest, g0.flt -> group_fault_01[0] 483.7). So vC2 needs a new placement or pin cycles on the final. That is a new decision, not a replay.

Gate:
- Hard-core overlaps: 0 in all 81 types (every core inside its type outline).
- Restored instances vs d44v_gqi: outline and pins_file equal for all 82 (60 exp_x, 16 svgr_bk, 4 inj, 2 qcore), and origins equal too. The only mismatches are the 2 opsa_rest rows (not replayed) and the 4 kept exp0__l rows (full_x in d44v_gqi).
- No hard_cores row of any other module changes. Other per-type changes: 112 clock taps, 8 ft_slots, 2 internal_stations rows, all from part61/expx328. Top-level: note only.
- check.py --completeness --plan-geom report (intel1): base 984 ERRORs, new 984 ERRORs (both G0C FAIL, 64 pending-view, 1366 warnings); ERROR messages new-only 0, gone 0

Files: die_plan.json.gz, clock_entries.json.gz and core_macros.json (the final's sidecars plus the part61/expx328 changes; they replace the lower layers' copies), the 4 cores/ tables (copied from d44v/cores), corelat/cycles_svgr_bk_vB_1107.tsv, expx328_1107_event.json and expx328_1107_ft_nudge_ledger.json (this replay), restore_1109_event.json (per-module changes), tools/restore_1109.py.

Use: this holds the full plan, so it replaces d44v_corepins_1109 as the HBM final. Re-keyed types: q_hub_ne, q_hub_nw, q_su00, q_su01, q_su10, q_su11 (+ __physical_v1 of the q_su types). q_b113 does not change.
