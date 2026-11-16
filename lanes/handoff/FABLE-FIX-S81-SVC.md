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

## 09:12 PST svc_hi t3 kit_rtl PASS (closure applied on v3 + F2sv plan + v3 bind); kit_topology FAIL = missing lane file
- p3 svc_hi t3: kit_rtl RC 0 (closure log pmem/pvq/land/stage for ru_rsv_07_), then kit_topology FileNotFound on epyc2:
  s81-b3-clk/run/b/B6gG3b/src/physical/die_plan/s81/h2_2249/landed_sidecar_h2_psplit_all.json (lane path named by
  asbuilt_run.json; epyc2 has no s81-b3-clk lane tree). Staged that ONE file on epyc2 at the lane path (copy of the v3
  tree file, sha1 711c256fc96e = epyc9 lane file; README.fable-fix-s81-svc beside src/). asbuilt_run.json also names
  545 paths under B6gG3b/out (absent on epyc2; kit_rtl did not need them).
- svc_hi t3 relaunched as p4 (pid 3265257, intel2). svc_lo t7 p3 (pid 2995111) still in kit_rtl, will find the file.

## 09:15 PST COORD r310: svc-ready criteria (binding)
- Post svc-ready PASS only when BOTH pilots show: GRT overflow 0 AND TT setup >= -42 ps on the GRT-stage read
  (S81 RC x1.00, reloaded DB); OR post-CTS TT >= +45 ps before GRT. Post-CTS placement-RC under-reads by 51-86 ps,
  so a post-CTS value between -42 and +45 is NOT a pass. Plus my own: all macros placed at floorplan (148 / 169).

## 09:35 PST p4/p3 FAIL kit_topology: KIT_TOPOLOGY_BIND_STALE (real: v3 bind_out is the G3b-line bind, plan is F2sv)
- Fix: use DIE-S81-92 F2sv bind (epyc10 s81-b3-clk/run/b/B6gF2sv: bind errors 0, LATCHECK 873/873, bound on the v2 tree).
  Copied to epyc2 at the SAME absolute path: out/ (6.8 GB), asbuilt_run.json, sidecar_new.json (a3b57fc803bf = ev sidecar),
  src/physical/die_plan/s81/h2_2249 (42 MB, asbuilt base + clock_landing_table).
- p5 launched 09:33 (intel2 pids svc_hi t3 3591211, svc_lo t7 3591571): v3 tree, plan_inputs/B6gF2sv_formA.json,
  bind_out/asbuilt/sidecar = B6gF2sv/{out,asbuilt_run.json,sidecar_new.json}, gen epyc2. Logs <item>/p5/.
- If p5 is BIND_STALE again, the 496 contents rows are in the bind fingerprint -> need a bind of the formA plan (F2s3).

## 09:27 PST COORD: F2s3 fallback
- F2s3 (epyc10 s81-b3-clk/ev/B6gF2s3.json + run/b/B6gF2s3) already carries the 496 svc site rows; rebind running (in G0
  at 09:25, no out/ yet). If p5 (F2sv bind) is BIND_STALE again: when B6gF2s3/out/bind_report.json shows errors 0, copy
  out + asbuilt_run.json + sidecar_new.json + src/physical/die_plan/s81/h2_2249 + ev/B6gF2s3.json to epyc2 (same paths)
  and launch both pilots as p6 with plan = B6gF2s3.json, in parallel with anything still running. svc releases off
  whichever passes r310 first. p5 is in kit_rtl at 09:25.

## 09:50 PST p5 (F2sv bind) FAIL kit_rtl on BOTH pilots: memory closure refuses the F2sv bound (cause (a) NOT closed on the F2s line)
- Error: s81_svc_memory_closure.py "reference net 673_Y not structurally mapped" (svc_hi t3; svc_lo t7 same stage).
- MEASURED: ref_1116 was regenerated from the G3b LANE bind, whose source run/b/B6gG3b/src has dsdv_svc_att.sv
  3c1f2d53cf3f (1016 lines) and ot_hdc_v41x_attn_tile_s.sv da37bbd0; main / v2 / v3 trees and the F2sv + F2s3 bind src
  have 7e6095d05c87 (1099 lines, +83 = ifdef OT_SVC_NATIVE_RT2_CALENDAR / OT_SVC_BAND blocks) and attn_tile_s 0464a4ce.
  svc plan type rows G3b vs F2sv differ only in clock. Bound svc_hi t3: 14448 lines (G3b) vs 14530 (F2sv); lo t7 +82.
  p3/p4 kit_rtl passed only because the v3 marker bind_out is the G3b-line bind.
- So EVERY main-source bind (F2sv, F2s3) fails the closure until the reference is regenerated from a main-source bound.
- My regen try (epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-svc/regen: pt/ = copy of the lane pt + v3 tools,
  bound/ = F2sv svc_lo t7 unclosed bound, new/ = main att+rs, old/ = lane regen/old): REFUSED, one token in the residual
  w_u_rsv_14_u_u_att_u_eng_111_Y (paired 5624, residual 1269/2163). Variants with --drop-loc running (regen_try.log).
- F2s3 pilots would fail the same way: do NOT launch them before a reference that closes the F2sv bound exists.


## CODEX notes 2026-11-16 10:26 PST
- Source fix pushed: claude/s81-svcmem-1116 @79ca679e3e0dd6a7f1164eeffadc05c660d85d6d. New ref_1116_main original self-check12605dc2 PASS, current closure8e3c91c7, exact residual equality; CLOSED16/16 and fresh MAIN/F2sv kit-RTL APPLIED16/16; fit20kedges PASS+5mutantscaught. Oldref/failed evidence preserved,0cycles. READY posted; merge_ops owns one normal source gate. Optional pytest NOT RUN (epyc8 lacks pytest).
- Coherent private physical shortcut PROVED: canonical kit_topology prepare PASS on F2sv bind+F2sv_formA plan forhi3/lo7 (macro-content site rows do not change native contract), no bypass. Direct prepared kits epyc2 /srv/opentallas-scratch2/claude/fable-fix-s81-svc/direct_main2/<type>/rtl. Signed-view hash table copied exactly fromepyc10 to private in/signed_view_sha_s81.json after missing-path failure; direct_main/failed prep retained.
- Correct physical GEN includes --cland-pinslot all: clients intel2 490624/490625, logs ~/fable-fix-s81-svc/f2sv_main/genpins_<type>.log, outputs <direct_main2>/<type>/gen_with_pinslot. Earlier gen/ omitted pinslot and is evidence only, never route it. Both reviewed in epyc2 W/results/geom_review/svc_main_formA.{json,png} (148/169 macro/core sites,31newSRAMsites each).
- Intel2 watcher523030 ~/fable-fix-s81-svc/route_after_gen_main.py waits for both correct GEN exits, checks review, applies owner-removedcellcap0 before firstrun, replicates completed kits toepyc9, launches admitted48GB/8thread routes on epyc2/epyc9. Logs f2sv_main/route_<type>.log and route_watch2.log. Read macro placement148/169, then GRT overflow0 and TT>=-42 (or postCTS>=+45) before svc-ready. FullF2s3release tree/bind stillneeded; fleet_flow builds newref tree, do not duplicate these pilots.
- Added t6 geometry fix fornextplan: epyc10 W/t6_ft2_stage9_row.json moves ft2 stage9 all277sites and regs[9] +21.6um Y; macro/band intersections0, previous maxhop247.32um,0cycles. Sent s81_plans forF2s4.
- Old svcsynth t6/merge_test_hi4 remain CPU-active evidence-only superseded nonclosure forms, not release pilots (S81-BKSEL-O diagnosis).

### 10:37 PST both physical pilots LIVE
- Correct GEN exit0 both, macro_place148/169; both admitted48GB/8threads on epyc9 in direct_main2/<type>/gen_with_pinslot/<type>: hi3 unit oth-ubuntu-1058252-1794853757, lo7 unit oth-ubuntu-1065422-1794853797. Both KIT_PREFLIGHT PASS0 and now1_2_yosys (OPT progresses). Intel2 route_TYPE.log holds dispatcher, kit/run/logs/... stage logs on epyc9. Scratch epyc9 332GB / epyc2 113GB free. Earlier omitted-pinslot GENs completed and are not routed.
- GENBUG d7bebc047fe1d9124f2694d738ad36f06294a192 is the sole unused-emitter classfix, normal gate owned elsewhere. My duplicate private prototype was stopped by verified exact PID2964569 after8s, unit2964133 exit143; no source edits/commits and no P&R interruption. Future genuinely needed GENs may take the approved fix. Current pilots untouched.

### 11:39 PST canonical synthesis-profile repair (current physical pilots)
- Confirmed construction omission: canonical dies.s81.item_env has OT_SYNTH_ARGS=-noshare for BOTH hi3/lo7; eight-lo-type annotation includes lo7, hi3 had it already. Old random-template private spec lost this field. Every other effective die/item gen env matches (private signed-table path is byte-identical relocation; FLOW_TAG is metadata). Actual gen_phys maps it to export SYNTH_ARGS; running ORFS synth.tcl consumes it and Yosys accepts -noshare.
- Correct existing-profile fresh copies NOW LIVE on epyc9: W/approved_profile/<type>/gen/<type>, 48GB/8threads, hi3 unit oth-ubuntu-1851452-1794857871, lo7 unit oth-ubuntu-1851446-1794857871. Both preflight PASS0. Only SYNTH_ARGS=-noshare restored plus qualified D2 PG replay helper files before first launch; RTL/plan/148169macros/geometry/latency unchanged. profile_restore.json captures full canonical env. Old direct_main2 runs remain intact but are explicitly mismatched-profile evidence; do NOT use them alone to release canonical wave types.
- launch_pilot.sh now recomputes exact canonical die_gen_env+item_env for selected type instead of inheriting random-template env (backup launch_pilot.pre_codex_itemenv_1116.sh, bash-n PASS).
- Required F2s3 canonical-release16SVC APPLIED check admitted EP10: client2123808/unit3092088, W/release_family_check.py, out W/f2s3_canonical_family1; log intel2 f2sv_main/f2s3_canonical_family1.log. Uses canonical bind0/LAT873 plan/ASB/out and published D2 newref source. Does not wait for unrelated path-only bind repack/ep9fanout owned fleet_flow; no new P&R duplication.
