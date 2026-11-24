# QC-STSLW-ROUTE handoff (narrow lane from QC-ALLFIX, 11-24 15:0x PST)
Job: 4 QC route kits FAIL "deepest grt failing SETUP_TRIAGE,drv,final" exit 6: sle_st_a_v1 cl18eece69, sle_st_a_v2 pv88773f93, sle_stm_v1 clbe630b9c, slw_st_a_v1 clb036e152.
## CLASS-CAUSE (posted 15:16)
One stop: post-CTS setup_est -153/-174/-178/-171 < -150 (PLAN-TRIAGE); drv slew 64-209 and grt_policy are residue; GRT ov 0. Each worst path = 1 unstationed leg 740-1300 um (9-25 repeaters).
(1) 11 st_a types on C1h..C1k lack QC-OPEN-STA r10 (cG, plan_c1g_sta10 3c17478ed804): passers are r10 grt kits (setup_est -14..-18). (2) cl18eece69 + clb036e152 lack landing_relay_start_copy (siblings true). (3) sle_stm lacks bus:flt_o 2 stations + E lane fixed 2 (slw_stm has it).
## ROW STSLW-R1
epyc7+epyc11 /srv/opentallas-scratch2/claude/QC-STSLW-ROUTE/: stslw_row.py BASE OUT r10_delta.json (r10_delta from make_r10_delta.py, guarded by C1g md5s). Applied to c1k.json 7fbc73d3f7cf -> rows/plan_c1k_stslw.json 462b3c863bb6.
Skipped (base moved on clock.landing_contract.pins): sle_st_a_v2 pvd2ec7769, pv4242de79 -> hand rebase for C1l.
## Pilot
Fork cK tree -> epyc11 cS/tree (unit oth-ubuntu-1882618-1795562310). Then: bindS.sh cS rows/plan_c1k_stslw.json 462b3c863bb6 (PRE, elab, strict bind, LATCHECK; OT_C1H_RT=rt/1145a6e17e79), then launch_stslw.sh route sle_st_a_v1__cl989804f6__cl18eece69 (pilot). Family after pilot sign-off: sle_st_a_v2__pv30dda31f__pv88773f93, sle_stm_v1__clbe630b9c, slw_st_a_v1__clb036e152.
