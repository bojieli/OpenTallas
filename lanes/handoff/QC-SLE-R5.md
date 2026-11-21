# QC-SLE-R5 handoff (Sonnet 5.5, started 2026-11-21 10:55 PST; successor to OPUS-FIX-QC-SLE-R4)
Family: QC sle_ctl / sle_sc / sle_stm (+ su_c per R4 handoff).
## State 11:05
- sle_ctl cla4f6f12f: R4 variant C (k_c, epyc9, launched 10:35 after bind c4) still running; R4 drives it. V2 plan (b20, strict bind/LATCHECK/G0 PASS) carries sle_ctl; V2 event qwen_compute s29q103S4Q9N46R6V2 apply pending (QC-PLAN-R10 10:24). Wave relaunch of sle_ctl on V2 comes from that event. R8 opt-ins (STRAP commit 33d25422f0) NOT on main: push died rc4 test_schema_file_in_sync (STRAP-R2 to regenerate schema). Waiter: schema.py in rt/current contains r_r8_core_seat.
- sle_stm_v2 cl7b3062fa: NOT superseded (still in V2 bind.f). V2 die_plan has no reset.inst_taps row; row 2b2dfe128b06 (tap 79, sinks u_core, leg 699->190 um, 0 cycles; stm_rows.json on epyc7 opus-fix-qc-sle-r4-rows/stm) must ride V3 (QC-PLAN-R10) or a private plan on b20.
- Other sle_* unsigned: sle_su_c, slw_su_c cl19bb38ef/cl92142dac, sle_sc_v1 cl115da35f, slw_sc_v2 (R4-SC), sle_stm_v2 cl55be2264, sle_stm_v1 clbe630b9c (export stuck, FAM-QC-FEFW-R2): all running, none signed yet.
