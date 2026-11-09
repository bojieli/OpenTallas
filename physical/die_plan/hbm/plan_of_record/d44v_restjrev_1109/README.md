# d44v_restjrev_1109: HBM final plan d44v_restore_1109 + event restjrev_1109

Built by DIE-HBM-97/RESTORE on 2026-11-09 with tools/restjrev_1109.py (copied here), per DIE-HBM-97 decision (a). The input was d44v_restore_1109/die_plan.json.gz (sha256 27e46e2d84777acf) with its sidecars. No gz was hand-merged.

Plan `die_plan.json.gz` = sha256 6cc23d9671508730 (uncompressed, json indent 1 as the final).

| step | event | module | instances | what changes | table |
|---|---|---|---|---|---|
| 1 | restjC_1108 inverted | ot_hgi_sfu_split3_ctl_rest_1c | 2 (q_b113(+__physical_v1) u_sfucore_Q_ctl__rest) | 267.84x267.84 at (587.52, 1105.92) -> d44v form 427.68x453.6 at (509.76, 1010.88); track_offset [-0.096, -2.112] -> [-0.096, 0.0]; pins_file; 2 clock taps [721.344, 1237.632] -> [721.344, 1235.52]; 2 clock_entries [133.92, 133.824] -> [216.0, 224.64] (+ island); core_macros entry outline back; the RESTJ-C-1108 note suffix removed from row, tap, clock entry and core_macros notes | cores/ot_hgi_sfu_split3_ctl_rest_1c__427.68x453.6__d44v_split.json |
| 2 | opsarest_c2_1107 (834d940a5e) | ot_hgi_sfu_opsa_rest | 2 (q_b113(+__physical_v1) u_sfucore_Q_opstore_a__r) | mk_opsarest_c2.py unchanged: 760.32x86.4 -> 250.56x64.8, MX at (1131.84, 959.04); 2 clock taps, 2 clock_entries (125.28, 32.4); 24 station chains per type re-anchored (12 launch, 12 capture), 1 re-sited per type with the same register count | cores/ot_hgi_sfu_opsa_rest__250.56x64.8__d44v_opsarest_c2.json + corelat/cycles_opsarest_c2_1107.tsv |

Step 1 is the exact inverse of restjC_1108_event.json (DIE-HBM-92-RESTJ RESTJ-C-1108). Every die_plan row, clock entry and core_macros value it recorded is set back to its recorded 'old' value. Asserted: the plan held the event's 'new' values, and the result equals d44v_gqi's row and tap, d44v's clock entry and d44v's core_macros entry. RESTJ-C-1108 changed no internal_stations, and none are changed here. The top-level note gains a restjrev tag (history kept).

Pin check (as corepins_1109, kit face pins inset 0.096): the 427.68 table vs the signed record's kit pins.json (epyc4 /srv/opentallas-scratch3/claude/die-hbm-88/r1c/eco_one_b/i1, signed_records hbc_ot_hgi_sfu_split3_ctl_rest_1c, local SIGNED / LOCAL_PASS_NEEDS_PARENT; pins.json sha256 8606b7288341444a). Names 12373/12373, 0 layer changes. All pins match except one: clk, the entry pin. The kit has 216.024 (entry 216.0 + 0.024); the d44v table has 215.976 (entry - 0.024). That is 0.048 um, within the 0.1 kit-vs-table tolerance of mk_p60 / mk_p61. Both 0.048-wide rects end on the entry x 216.0.

Step 2: with ctl_rest back in the d44v form, mk_opsarest_c2.py passes its own reach assert. Every moved reg-to-reg link is <= 452.5 um, the same links and values as d44v: ctl_rest -> scalar_data 424.8, scalar_load 436.1, scalar_load_addr 431.7, stage_group 435.2, stage_v 435.8, and g0.flt -> group_fault_01[0] 436.2. PIN CYCLES 0, fault 0. The opsa_rest rows equal d44v_gqi's in origin, outline, pins_file and orient. The table is byte-equal to d44v/cores.

Gate:
- Hard-core overlaps: 0 in all 81 types (every core inside its type outline).
- Changed vs 27e46e2d: only the 2 x 2 rows above, 4 clock taps, 48 internal_stations rows (q_b113 / q_b113__physical_v1, opsa_rest chains), clock_entries 4, core_macros 1, top-level note.
- check.py --completeness --plan-geom report (intel1): base (27e46e2d, chk_new) 984 ERRORs, new 972 ERRORs (both G0C FAIL, 64 pending-view, 1366 warnings). ERROR messages: gone 22, new-only 10. The gone ones are 12 hard_cores off-track pin rows of the restjC ctl_rest (2706 pins per type) and 10 core_faces rows. The 10 new-only rows are all [core_faces] in q_b113 / q_b113__physical_v1: opsa_group g0 rd_addr / rd_re E face, g0 scalar_enable N (cos -0.89, was -1.00), g1 rd_addr E, and the 2 per-type summary lines, all facing away from the compact u_sfucore_Q_opstore_a__r. The same rows, word for word, are in the G0C reports of d44v, d44v_epm, d44v_gqi and d44v_gqi_cp1109 (release_tree g0c_reports): they come with the vC2 form as the d44v lineage holds it, and opsarest_c2_1107_event.json lists the rd_addr / rd_re spans as 'not_measured_here' (the type build times them). So the strict gate new-only 0 is NOT met. The 10 rows are not new to the plan of record.

Files: die_plan.json.gz, clock_entries.json.gz and core_macros.json (they replace the lower layers' copies), cores/ (the 2 tables, copied from d44v/cores), corelat/cycles_opsarest_c2_1107.tsv, opsarest_c2_1107_event.json (this replay), restjrev_1109_event.json (per-module changes, pin check), tools/restjrev_1109.py.

Use: this holds the full plan, so it replaces d44v_restore_1109 as the HBM final. Re-keyed types: q_b113, q_b113__physical_v1. A full staged plan dir with fresh SHA256SUMS is at intel1 and epyc7 /srv/opentallas-scratch2/claude/die-hbm-97/plan_r3_restjrev/ (DO_NOT_COUNT).
