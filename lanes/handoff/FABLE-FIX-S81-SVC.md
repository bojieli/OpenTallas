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

## 07:15 PST update (COORD: own svc to sign-off)
- (c) rows DONE and posted (DELTA-ROWS 07:0x): epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-svc/formA_sites_B6gG3b.json
  sha1 10cf7d27bf9f, generator svc_formA_sites.py PLAN OUT. 31/31 placed on 16/16 types, no outline growth.
  Not checked: composed bands / N-face pin windows in the strip; instance names INFERENCE until a pilot netlist.
- S81-SVCMEM-1116 06:51: ref_1116 closes svc_hi t3 + svc_lo t7 offline (epyc9 kp/, pt/). Waiting on its commit + gate + READY,
  then TOOLS-CONVERGE S81 v3 delta tree (v2 + ref_1116 + tools/die_plan/s81_svc_*).
- DIE-S81-92: asked for ONE svc delta B6gF2sv = 31 rows x svc types + ring ff stamp + drop svc exemption. No ACK yet.
- Release token: HOLDGEN releases svc on "RESULT FABLE-FIX-S81-SVC svc-ready". Post ONLY after pilots svc_hi rs t3 +
  svc_lo rs t7 pass floorplan (76 / 97 macros placed), GRT, and look likely to sign off. Pilots are not held.
- Pilot recipe: private kit_wave.py run-item (pattern intel2 ~/svcmem/<item>/spec.json) or the wave item itself, with
  plan = F2sv, src = v3 tree, hosts without epyc10. Wave defaults: kit_wave.json dies.s81 (gen_args --hold-ff-margin 0
  --max-wire-um 100 --clock-landing <sidecar>).
- Decided NOT to hack a B6gG3b private pilot around the unpublished closure files (duplicates the lane, wrong plan).

## 08:05 PST update
- COORD ruling ~08:00: do NOT wait for DIE-S81-92; start svc_hi rs t3 + svc_lo rs t7 as private run-items the moment the
  S81 v3 marker posts (TOOLS-CONVERGE, build started 07:37, carries B6gF2sv_formA.json 626de2b41910 in-tree), not on
  epyc8 (disk) / epyc10. DIE-S81-92 folds the 496 rows into F2s3.
- (b) CLOSED: ev/B6gF2sv.json (= stamped plan 4c163bdc1625) has ring ff on all svc bands.
- (a): r298 approved (claude/s81-svcmem-1116 @89627948e87); lane private gen svc_hi t3 gen_lint memory_bits PASS.
- Launcher READY: intel2 ~/fable-fix-s81-svc/launch_pilot.sh ITEM SRC PLAN SIDECAR BIND_OUT ASBUILT [MANIFEST_HASH] [TAG]
  (spec from the newest S81 wave spec; gen_host epyc9; hosts intel1 epyc9 epyc2 intel2 epyc7; work
  /srv/opentallas-scratch2/claude/fable-fix-s81-svc/pilot/items/<item>/attempt_<tag>; logs ~/fable-fix-s81-svc/<item>/<tag>/unit.log).
  Take SRC / plan / sidecar / bind_out / asbuilt / manifest hash from the v3 marker post.
- Reads: gen_lint + preflight, floorplan placed macros 148 (hi t3) / 169 (lo t7), GPL, CTS, GRT, route, R-MINIMAL gates.
  Then post exactly: RESULT [FABLE-FIX-S81-SVC -> COORD] svc-ready PASS: <evidence>.

## 08:45 PST pilots LAUNCHED (private run-items, v3 tree)
- svc_hi_dsdv_svc_rs__t3 pid 2601519, svc_lo_dsdv_svc_rs__t7 pid 2601838 (intel2 run-item; kill exact PIDs only).
  logs intel2 ~/fable-fix-s81-svc/<item>/p1/unit.log (+ stage logs); work epyc9
  /srv/opentallas-scratch2/claude/fable-fix-s81-svc/pilot/items/<item>/attempt_p1.
- Inputs: src kw45/src_s81_pin_41bb1dcfd10a (manifest 3a6408ed...), plan in-tree plan_inputs/B6gF2sv_formA.json
  626de2b41910, sidecar epyc9 fable-fix-s81-svc/in/B6gF2sv_sidecar.json a3b57fc803bf (copy of ev/), bind_out
  kw45/s81bind_pin_41bb1dcfd10a/out, asbuilt s81-b3-clk/run/b/B6gG3b/asbuilt_run.json.
- RISK: the v3 bind_out was bound on plan_h2_2249 (G3b line), the pilots use the F2sv plan: a kit_rtl / LATCHECK
  mismatch on svc would show at kit_rtl or preflight -> then ask DIE-S81-92 for the F2sv bind out on v3.
- RISK: epyc9 scratch2 31 GB free at 08:40; tree only on epyc9 + epyc10.
- Launcher fix: no pipefail (ls|head SIGPIPE killed it silently).

## 08:58 PST pilots RELAUNCHED as p2 (p1 failed kit_snap: epyc9 scratch2 27 GB < 50 GB store floor, INFRA)
- p2 pids (intel2): svc_hi rs t3 2788430, svc_lo rs t7 2788774. Work root now epyc9 ROOT disk
  /srv/opentallas-scratch/fable-fix-s81-svc/pilot (414 GB free after a 7.2 GB snapshot); logs ~/fable-fix-s81-svc/<item>/p2/.
- p2 passed src_manifest, kit_snap, bind_fetch, bind, kit_rtl_probe; in kit_rtl at 08:57.

## 09:05 PST pilots RELAUNCHED as p3 on epyc2 (p2 failed kit_rtl: ot-run refuses a root-disk --dir on epyc9; INFRA)
- p3 pids (intel2): svc_hi rs t3 2994618, svc_lo rs t7 2995111. gen host epyc2 (v3 tree + bind present, 184 GB free),
  work epyc2 /srv/opentallas-scratch2/claude/fable-fix-s81-svc/pilot/items/<item>/attempt_p3; logs ~/fable-fix-s81-svc/<item>/p3/.
  Lane inputs staged on epyc2: fable-fix-s81-svc/in/B6gF2sv_sidecar.json a3b57fc803bf; asbuilt_run.json was there.
- p3 passed src_manifest, kit_snap, bind_fetch, bind, kit_rtl_probe; kit_rtl running 09:01.
- My epyc9 root-disk pilot dir + the root kit-store I created (7.2 GB) are deleted.
