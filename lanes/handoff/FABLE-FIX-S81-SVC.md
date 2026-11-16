# FABLE-FIX-S81-SVC handoff (owner of the S81 svc family), 2026-11-16 06:5x PST

## Root causes (all MEASURED unless marked)
(a) Memory check. The plan is already in the MEM v2 macro form: every svc type has 45 SRAM sites (8 x 160x265 staging
    `...g_stage2_u_stageN.g_macro.g_fit.g_lane[l].u_mem`, 12 x 160x256 land_capture, 4 x 256x256 pmem_capture,
    17 x 32x128 pvq_capture, 4 tgt banks). The kit RTL reaches that form only through kit_rtl_post.d/s81_svc_memory.sh ->
    tools/die_plan/s81_svc_memory_closure.py --form v2. On the B6 bind (-DOT_SVC_ATT_MEM_MACRO) the closure refuses the
    bound (reference ref_1112 no longer matches; S81-SVCMEM-1116 05:54), and the S81-SVC-SYNTH pilot kits skip the post
    step. So the kit keeps the behavioural staging (4 x 160 x 265 = 42,400 b) plus pmem/land/pvq natives.
    r274 memwr merge and the GENBUG g_macro160 branch do not cure it: g_macro160 names do not match the plan sites and
    pmem/land/pvq would become ~440k flops.
(b) ring_place ff lost on 82 frozen svc bands: fixed at the tool (r282 526fc2be53d, S81-RINGS-O). Open: the F2s plan
    still needs the key stamp (epyc10 fable-fix-s81-rings/ring_ff_stamp.py, out stamp/B6gF2s_svcff.json 4c163bdc1625)
    or a re-compose on main; DIE-S81-92 owns it.
(c) NEW: the 31 form-A macros that -DOT_SVC_ATT_MEM_MACRO adds (u_att wq_mem 6 inst = 18 x 32x128, u_qmem_mem 4 x 32x128,
    u_sw_mem 8 x 32x128, u_rsv u_pbuf_mem 1 x 160x256) have NO site in plan B6gG3b contents (16/16 svc types;
    macro_place.tcl of the B6gE svc_hi t3 kit: 117 rows, 0 for these). INFERENCE: with MACRO_PLACEMENT_TCL set they
    stay unplaced into global placement. No svc kit has reached floorplan on B6, so this is not yet observed.

## Decisions (owner)
1. Fix for (a) = regenerate the closure reference for the B6 bind (ref_1116), S81-SVCMEM-1116 does it (epyc9
   /srv/opentallas-scratch2/claude/s81-svcmem-1116, s81_svc_ref_regen2.py; svc_hi t3 SELF-CHECK PASS 12605dc2 seen in
   regen2.log, svc_lo t7 running 14:25Z). 0 added cycles, no plan change, no LATCHECK rows.
2. GENBUG claude/attn-staging-160x265-1115-1 (g_macro160) is NOT used for svc. No mem2reg flops for pmem/land/pvq.
3. Accept for (a): closure APPLIED on all 16 types; the 45 instance names equal the plan contents; fit gate
   (results/rtl/s81_svc_memory_fit_1103/run.sh, Verilator vs native + mutants) re-run on ref_1116; kit LEC per type.
4. (c): delta rows requested from DIE-S81-92 (31 sites per type). Proposed form for svc_hi (free strip y 2548..2747):
   row y 2559.6: 26 x 32x128 at pitch 52.4 from x 43.2; row y 2591.4: 4 x 32x128 + the 160x256. svc_lo top is full
   to y 2727 (idx macros): next row above, Y growth if needed (pre-approved). Check against the composed bands there.
5. Pilot order: svc_hi rs t3 + svc_lo rs t7 on the v2 tree src_s81_pin_eb1e73448bd0, not epyc10; read floorplan
   (macro count placed = 76 / 97) before judging anything later.

## Not mine / in flight (do not duplicate)
- S81-SVCMEM-1116: ref_1116 regen (epyc9), branch claude/s81-svcmem-1116 (epyc8 clone, no commit yet).
- GENBUG/S81-SVC-SYNTH epyc8 merge_test_hi4 (svc_hi t3 synth, in ABC at 14:00Z): evidence only, form not adopted.
- DIE-S81-92: F2s rebinding on the v2 tree (epyc10, started 14:08Z).

## Next
- Read S81-SVCMEM-1116 READY; check the closure tool reaches the wave (it is read from the wave SOURCE tree, so the
  v2 tree needs ref_1116 + the tool change, or the reference travels in kit_rtl_post.d).
- Get the (c) rows + (b) stamp into the F2s svc plan, then lift the svc hold and build all 10 F2s svc types to sign-off;
  export signed records to AGIdock /archive/opentallas-signed-1114 and rtx-pro.
