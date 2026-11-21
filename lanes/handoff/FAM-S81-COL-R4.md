# FAM-S81-COL-R4 handoff (started 2026-11-21 05:3x PST, Opus; successor of FAM-S81-COL-R3)
Scope: col_h9_r1 + col_h9_r2 (118 types held for J7) + shared J7 col rows (XALIGN, FIT CHAIN, relay_mid depth). Lever 1 (RDX/ROM, OT_S81_CFG7_RDX) = FABLE-FIX-S81-COLROM. h9_r0 = FAM-S81-COL-H9R0-R2. h10 = FAM-S81-COL-H10. J7 assembly = S81-J6-ASSEMBLY-R3.
Dirs: intel1 /srv/opentallas-scratch2/claude/fam-s81-col-r3 (R3 files, binds); intel2 same path (chains, wave5 spec); epyc10 /srv/opentallas-scratch2/claude/fam-s81-col-r4 (my new jobs).
## Running
- bind4 (XALIGN gate, src4 = J5 + XALIGN) and bind5 (h9_r1 rep src5 = J5 + mkplan2 lever-1/RDX + XALIGN), intel1 ot-run, logs bind4_otrun.log / bind5_otrun.log.
- hub chain5.sh (R3, setsid) waits bind5 -> kit_wave run-item wave5/spec.json -> place, posts result. 05:4x I fixed wave5/spec.json (copy+mv, original spec.r3orig.json): gen_env = exact die_gen_env+item_env of col_h9_r1__t1__cl49d7a23e (removed h10 OT_CONS_*, added 9 h9_r1 keys), hosts epyc8/epyc10/epyc7. Wave kit config.mk for diff: J6 kit epyc9 kw43-wave-1109n/.../dc92652f0d5/items/<T>/attempt_2/gen/<T>/config.mk.
- epyc10 fam-s81-col-r4/rd: relay_depth.py report on ^col_h9_r[12]_ (J5 plan + J5 bind rtl), report-only.
## Findings
- Earlier rep pv047ea3b3 (event 465cb9fe2d3) ROUTED + sign-off on epyc2 ot-jobs (11-20 16:53): NOT SIGNED, TT 535 endpoints < -42. Classes: u_t4/xai 33 ends -291.5, u_t5/xbi 34 ends -184.8 (relay u_u_y_xa_4_0 / xb_5 output, ONE unbuffered net: slew 2,411 ps, 761 ps wire), cfg7 s*.q 98 ends -143.9 (RDX), ROM xs_q*/cfg_d 330 ends -84 (lever 1). The xai/xbi class = relay depth rows (405 um), mine.
## Next
- On bind4 green: g0.sh src4 g0_x; L02 e1 schedule check (TOKEN-1121 stood down): epyc10 tok-verify-2/recovery1116/j5_capture1121/f3_siblings (schedule_L02_r5, compile_down_l02.py).
- t4.xai/t5.xbi depth rows for h9_r1/r2 from the relay_depth report -> S81-J6-ASSEMBLY-R3 for J7 (mkdepth405 ^col_ should already cover; verify).
- h9_r2 S-edge pin row (x 302-346, y 0): read at GRT iteration >= 10 before any row.
- Delete src3/src4/src5/bind/bind4/bind5 via ot-delete when their jobs end (keep logs).
