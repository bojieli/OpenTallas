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

### CODEX 2026-11-16 actual F2s3 pilot correction / obsolete t6 disposition
- Mainref source79ca679 and canonical F2s3/D2 all16APPLIED remain PASS; no-op CLI fix5f3b4a1 normalgate GREEN full closure test file, proof-only successor f255500 pushed READY.
- Important correction: F2sv private pilots are not byte-identical F2s3 RTL. Difference classified reset-only (+28 hi3 / +112 lo7 relays), timing-relevant. Earlier runs retained as source/profile cause evidence, not release qualification.
- Actual adopted F2s3 closed hi3/lo7 selected GEN now ep10 fable-fix-s81-svc/f2s3_actual_phys/TYPE, tools-converge/s81/gen_e37_D2_exec plus D2 rtl-root; exact fresh canonical die/item env incl-noshare, no removed reach0/M9/congestion override. PREP0; GEN progressing.
- Actual plan+captured reset review PASS-COND: ep10 fable-fix-s81-svc/results/geom_review/svc_f2s3_review_reset.{png,json}. Intel2 watcher1047974 route_after_f2s3_actual.py waits GEN0, checks review+profile, copies completed kits to ep9, normal48GB8thread routes. Logs f2sv_main/finalgen_TYPE.log and f2s3_route_TYPE.log.
- Root-authorized superseded inherited epyc8 t6 STOPPED exact unit oth-ubuntu-952570-1794791581. Sole exact-dir consumer dpkit-svc_lo_dsdv_svc_rs__t6-952645 confirmed, scope inactive and Yosys3335451 gone. Original svcsynth-1115/svc_lo_dsdv_svc_rs__t6 objects/logs preserved plus immutable SUPERSEDED_NONMACRO_1116.json (source SHA/no closure receipt). Not a release pilot.
- r310 svc-ready physical result remains HELD until actual F2s3 timing/GRT result. Two source-event prerequisites may advance to adopted B6gF2s3; retain physical result hold/history.

### CODEX actual F2s3 physical launch milestone
- Selected hi3/lo7 GEN BOTH PASS0 (e37/D2); exact canonical closed input identity receipts PASS129/153files at f2s3_actual_phys/TYPE/canonical_rtl_identity.json. Only generated differences are planned hard-core header-only views; reset/datapath exact.
- Both routes admitted ep9 48GB8threads, preflight PASS0: hi3 unit oth-ubuntu-3006868-1794863068, Docker11251cfb0840 dpkit-svc_hi_dsdv_svc_rs__t3-3007103 actively synthesizing. Lo7 unit oth-ubuntu-3031332-1794863108, exact Docker request dpkit-svc_lo_dsdv_svc_rs__t7-3032295 still pending startup (client3041140, no container object yet). Preserve both, no duplicate launch.
- Original path root fable-fix-s81-svc/f2s3_actual_phys/TYPE/gen/TYPE; intel2 f2sv_main/f2s3_route_TYPE.log; watcher1047974 retains terminal results.
- EP9 scratch dipped46GB, recovered130GB then73GB: unrelated large writes; fleet_flow owns capacity/create-pending diagnosis. Own new kits under150MB. Hi3 progressing synthOPT3.8, lo7 pendingDocker is INFRA observation, not designFAIL.

### CODEX latest live status (supersedes startup observation above)
Lo7 Docker startup resolved normally without any retry: b34e72db8af9 / dpkit-svc_lo_dsdv_svc_rs__t7-3032295, synthesis active. BOTH actual F2s3 pilots live; hi3 unit3006868, lo7unit3031332. Measured containers~9.6/11.9GiB against48GiB each, CPU active; scratch~125GBfree. Canonical pair progressing OPT3.8; diagnostic oldF2sv approved-profile hi3 reached ABC15.42, lo7 MEMORY_COLLECT/OPT_CLEAN. No physical gate yet, r310 held. All source, t6 old-job and startup failures have explicit disposition.

## 13:30 PST FABLE back (limit 09:5x-13:2x; Codex covered, notes above)
- Not duplicating: the two release pilots are the Codex-launched ACTUAL F2s3 kits on epyc9
  /srv/opentallas-scratch2/claude/fable-fix-s81-svc/f2s3_actual_phys/<type>/gen/<type> (hi3 unit oth-ubuntu-3006868-1794863068,
  lo7 oth-ubuntu-3031332-1794863108; route goal, 48 GB / 8 thr; intel2 watcher pid 1047974). 13:28: both in 1_2_yosys
  (hi3 OPT 3.8.175, lo7 3.8.62); macro_place.tcl rows 148 / 169 = plan sites incl. my 31; epyc9 scratch2 119 GB free.
- Closure on main source solved by Codex (ref "mainref", source 79ca679, 16/16 APPLIED on F2s3). F2s3 adopted (r331).
- My p1-p5 run-items are all ended (AP_END); epyc9 regen/ dir is evidence only.
- Next reads, in order: 2_1 floorplan placed macros (148 / 169), GPL, CTS TT, GRT overflow + GRT-stage TT (r310), route.
  Then: RESULT [FABLE-FIX-S81-SVC -> COORD] svc-ready PASS: <evidence>.

## CODEX resumed 2026-11-16 14:23+ — source inventory diagnosis
- Source/result-only claude/s81-svcmem-1116 @ba8e06b7227b6e1e567da7a67f6ebd8fa941265d pushed: results/rtl/s81_svc_memory_fit_1103/live_inventory_1116/ holds exact producers/all consumers for both selected canonical and diagnostic source, plus declared/live area price. No source RTL edits or proof replay.
- Diagnostic approved-profile F2sv hi3 Yosys measured140 total/23formA macros (all actual names in plan). Missing8 are exactly six WQ third128b banks and QMEM third/fourth128b banks. Each WQ W341 helper connects256b wd/rd and consumer explicitlyzeroextends85b; QMEMW512 connects256b wd/rd, consumer explicitlyzeroextends256b. Same7 producer/consumer records in canonical F2s3 hi3 AND lo7.
- COORD r369 now permits only this exact8 declared/live interpretation: keep31declared sites/outline/unused slots; canonical selected netlist must confirm exact8 names before140hi3/161lo7 counts. No genericmissing waiver/KEEP/source-bit change. Live131072bits/27173.656512um2 vsdeclared163840bits/35735.23296um2: -32768bits/-8561.576448um2,+0cycles/+0throughput.
- Actual canonical F2s3 pilots remain original EP9 units3006868/3031332, no restart/GEN/proof duplication. Authoritative progress is kit/run/logs/asap7/dp_TYPE/base/1_2_yosys.log (host run_route.log lagged/truncated during ENOSPC). Latest hi3ABC15.42, lo7fineOPT4.1; ~20/23GBRAM. Diagnostic hi3 mapped140macro netlist+1_synth.odb exists and passesSELRANGE,PORT_BIND,FACE_GUARD19556,REG_FANOUT653491/over64=0; in2_1floorplan pre-repair, not releasequalification.
- EP9scratch fell3GB/1GB, root r368guarded capacity emergency handled; now~131GBfree. All activejobs/logs/objects preserved. r310svc-ready remains HELD until actualcanonicalphysical TT/overflow read. r371/RULEBOOK519–526 RMIN: DRC0/routedTT>=-42/internalregFF>=0 +functionalbind/LATCHECK; asynchronousLEC and parentporthold advisory, knownfunctionalerrorsnotwaived. Never wait asyncLECalone after actualphysicalpass.

### CODEX corrected hi3 dispatcher status — 2026-11-16 15:2x PST
- Original canonicalhi3 ot-run unit3006868 returnedexit1 at14:44:20, duringENOSPC; original intel2 f2sv_main/f2s3_route_hi3.log retained (full TYPE filename). Earlier stage-only statement bothunitslive was inaccurate: hi3unitinactive, lo7unit3031332 stillactive.
- SAME hi3Docker11251cfb0840 remainsrunning/OOMfalse with FULL innergoalroutebash3010150 -> grt183_make3028872 -> make3029369 -> logger3043061 -> Yosys3043062 -> ABC373994. This is not an ABC-only orphan. stdout/stderr stillhavecontainerd-shim3010126 READfds11/13; logger/Yosys/ABC pipepairs alllivereaders. No stdoutpipeintervention or restart needed.
- run_kit.sh:501 redirects DockerCLI to E9K/run_route.log; fullfilesystem+partiallastline supportouterattach/log-writefailure inference (expliciterrorunavailable). Innerflowcancontinuefloorplan/CTS/GRT aftersynth. lec_async.mode=unit, so abortedhostLECwatcher willnotstrandinnerphysicalwait; R371asyncadvisory applies.
- NEW readonlyobservation intel2PID3149019 ~/fable-fix-s81-svc/observe_existing_hi3_container_1116.py followsDockerlogs anddockerwait; recoveredconsole f2sv_main/hi3_container_recovered_console_1116.log, futureterminal hi3_container_observation_terminal_1116.json. Immutable lifecycle receipt hi3_dispatch_infra_lifecycle_1116.json pinsoriginalexit1/ownership/fds. No workrestart, currentkitpatch, duplicatejob orkill.
- Latest actualhi3activeABC with complete685MBinput; actual lo7OPT4.3 advancing. Scratch~125GBfree. R369exactcanonicalmacroconfirmation andR310physicalTT/overflow remainpending. Parentowns allbroaderflow/sourceintegration.

### CODEX 16:3x PST — actual canonical inventory and scoped placement candidate
- Canonical F2s3 hi3 SYNTH completed; exact netlist confirms140 total/23live formA, missing exactly r369-approved8, zero extra/missing-other macros, all45 legacy capture/staging. Evidence W/f2s3_actual_phys/hi3_canonical_synth_inventory_1116.json; result-only source0315fd5351f2651876712679710ce27ae3d0c458 pushed. Physical hold remains.
- Same original hi3 container11251cfb0840 now in2_1 floorplan pre-repair (iter758), full innerflow retained despite immutable outer dispatcherexit1. lo7 b34e72db8af9 still fine synthesis. Current/peak/max GiB hi3=22.22/31.38/48, lo7=24.33/29.35/48; memory.events all0. Fleet asked official live capacity growth mechanism and comparable actual placement evidence; no guessed cap change.
- Diagnostic old-reset F2sv hi3 terminal: completed2_1 object retained, then actual MPL-0020 on first exact dead WQ gm2 at2_2. This is placement declaration/live inventory contract, not canonical release data. Wait same canonical terminal; copied resume only after source approval, preserving SYNTH/2_1 and original failed evidence. No live patch/re-GEN/re-synth.
- Candidate582420b757467bf02ce5b5ada89b46fb9332a425 pushed on own SVC branch after clean currentmain merge. New defaultoff OT_S81_SVC_LIVE_SITES exact two-type helper and minimal partitionGEN hook: all8absent skips only8 literal placements, all8present delegates, mixed/wrongmaster/duplicate fails before placement, unrelated missing remains nativeMPL failure. Original31commands/outline retained; flagoff GENbytes unchanged. Eight focused actualTcl tests PASS; new real write_type_kit GEN integration node PASS1 on E8unit2797290. Earlier first attempt exit4 sparse physical/common_flow absent before collection retained. MQ owns ONE combined normal source gate, pending; no root approval/adoption claimed.
- Readonly family packet W/f2s3_actual_phys/family_r369_case_packet_1116.json shows all16 same seven producer/consumer zero semantics;14 plan-name matches, two PVSO t1/t2 rawplan prefix differs by extra_u, alias resolver review required. No allowlist expansion requested/applied yet.

### CODEX PARK to Claude 2026-11-16 16:58 PST

- PARKED immediately on Claude reset; no new launches/gates/source actions. Existing original canonical pilots continue: EP9 W/f2s3_actual_phys/TYPE/gen/TYPE (W=/srv/opentallas-scratch2/claude/fable-fix-s81-svc). hi3 container11251cfb0840 latest2_1 floorplan repair iter977; immutable original outer ot-run exit1 retained, recovered observer intel2PID3149019 remains. lo7 containerb34e72db8af9/originalunit3031332 in fineSYNTH EXTRACT_FA. Last measured RAM current/peak/max GiB hi3=22.22/31.38/48, lo7=23.65/29.35/48, max/OOM events0. Fleet live-growth/measuredfullshape PLACE request pending; no guessed cap change. E9S2 lastfree97GB.
- 582420b757467bf02ce5b5ada89b46fb9332a425 approved rootr385, MQ normalgate61/61 GREEN. Actual GEN node additionalPASS1. MQ owns merge/deploy; no merged mainSHA received at park. Preserve progressing pilots. Wait actual canonicalMPL-0020 terminal, then copiedresume with approved exact8 helper; canonicalhi3 netlist already confirms exact8 missing/140total/23live. R310 physicalhold unchanged.
- Copiedresume recipe PREPARED AS PROCEDURE ONLY, no copiedkit/launcher executed: preserve completedSYNTH and2_1_floorplan.{odb,sdc}; copy boundary2_1 rather than writablehardlink, hardlink safe priorcompletedobjects, retain originalfailure/logs. Change only copiedmacro_place.tcl by approved helper wrap, preserving all original31commands/geometry/outline; review receipt can document byteidentical placement geometry to prior actualreview. Standard kit_resume floorplan is coarse and do-floorplan reruns expensive2_1: copiedrunner must run exact remaining do-2_2_floorplan_macro/do-2_3_floorplan_tapcell/do-2_4_floorplan_pdn/do-2_floorplan/do-2_floorplan.sdc, then normalplace/cts/grt/route, keeping normal gates/done bookkeeping. No source/gate relaxation or proof repeat.
- Separate rootauthorized PVSO prefix candidate COMMITTED/PUSHED/clean own E8 /srv/opentallas-scratch2/claude/s81-svcmem-1116/repo branchclaude/s81-svcmem-1116 @3a528c3ac253050d47d47d86ab030867f66258ec. New s81_svc_pvso_paths.py/test +defaultoff OT_S81_SVC_PVSO_PATHS hook in bound_macro_paths.project. Exact2types only; unique canonical9 helper roots/dimensions prove31declared physicalpaths each, originallogicalnames/geometry/provenance kept; missing/duplicate/shape/master/partial contract negatives. Focused8PASS E8unit2908732, actualclosedcanonical bound31/31 both receipt in results/rtl/s81_svc_memory_fit_1103/live_inventory_1116/pvso_declared_paths.json. This is DECLARED31 path proof, not optimizedlivebank qualification; no8bankpolicyextension, no normalgate/adoption yet. Scratchcause W/svc_formA_sites.py names(r) hardcoded two_u where PVSO has three_u. Correction includes pbuf too:62names total. Earlier60name proposedpacket omittedpbuf and is superseded/unapplied; keep history. No uncommitted tracked source.
- t6 separate currentD3 successor constructor LIVE EP10 unitoth-ubuntu-1666367-1794876752, intel2client4133719, log~/fable-fix-s81-svc/f2sv_main/t6_stage9_819_constructor_1116.log. Exact W/next_t6_stage9_819/{candidate.json,delta.json,construct.sh,rtl}; base currentF2s4tapfix1 source plan, only ft2bit_sites_um[8]277sites andregs_um[9] +21.6Y verified,0cycles. Scopednormal kit-rtl then prepare-stations (no globalbind/currenteventmutation); last tap-limit INFO only, not terminal. Collect result next, render/review fresh currentkit before anyroute. Plans strip_refloor knows harness.
- No remaining unowned destructive action; no jobs killed/restarted, no cleanup performed. Owner questions: none new.

## CODEX SVC takeover 2026-11-16 19:5x PST
- Existing E8 hi3 `f2s3_mpl8/.../gen/svc_hi_dsdv_svc_rs__t3` progressing GPL, latest iter290/overflow0.9101; existing lo7 `f2s3_mq/.../gen/svc_lo_dsdv_svc_rs__t7` progressing OPT3.8.346. Neither restarted or patched.
- Actual hi3 3_2 placement ODB LOOK PASS-COND: 140 macros/0 overlaps, regular eight-column corridors and north SRAM rows. Image+record E8 `fable-fix-s81-svc/results/geom_review/hi3_mpl8_preGPL_1116.{png,json}`; read-only review unit467939-1794887128 EXIT0. Reinspect completed placement/CTS, physical svc-ready remains held.
- MQ source `de6d0ccfdec` targeted negative control PASS: read offset127 retained, bypass one tail output stage -> EL140 reference5799/5799 mismatches + absolute1395799, unchanged EL1240. E8 unit454579-1794887095 EXIT0; evidence `fable-fix-s81-svc/mq_negative_1116`, intel2 `s81-cores-r/mq-negative-codex.out`. Root notified for approval. Original lockstep unchanged5799/0; 276FF tail preserves139-delay/0externalcycles.
- t6 current819 stage9 constructor1666367 completed EXIT0, 141files/unbound0/problems[]. Rows E10 `next_t6_stage9_819/delta.json` ready for S81 die owner (ft2 sites[8] and regs[9] +21.6Y, 0cycles). No duplicate physical GEN/route.
- Next lo7: after SYNTH terminal confirm u_mq128x23/no1024x256, dump present macros, use exact-eight pdn_dead8 helper on stopped kit, review and resume physical. hi3: completed3_place image/CTS/GRT read.

## CODEX PARK — Claude reset reported by parent, 2026-11-16
- PARKED, no new work launches/source/kit edits after notice. Live E8 hi3 copied MPL/PDN resume still GPL iter380/overflow0.6814; lo7 mq-tail copy still SYNTH OPT3.8.371. Original intel2 clients hi3 unit3543253-1794880642 and lo7 unit4150398-1794884321 retained.
- Completed work: MQ de6d targeted one-stage-bypass mutant rejected5799/5799 (EL1240), E8 unit454579-1794887095 EXIT0; no proof rerun. Root has evidence/approval recommendation. hi3 actual preGPL macro review LOOK PASS-COND140macros/0overlaps, E8 results/geom_review/hi3_mpl8_preGPL_1116.{png,json}; read-only unit467939-1794887128 EXIT0.
- No own live job remains. Existing SVC jobs untouched. Next lo7 macro128x23 check + exact8 PDN projection after synth; hi3 completed3_place review then CTS/GRT. t6 stage9 row ready/constructorEXIT0, die owner notified. No new OWNER? item.

## CODEX SVC late takeover — latest physical progress
- Same E8 hi3 MPL8 run/container6ffbd6b426e9 preserved. GPL DONE (11684s), actual completedGPL ODB contains140macros with0positionchanges and4196872nonfillerstandardcells. Actual layout image LOOKED PASS-COND: regularmacrocolumns/corridors retained; north/eastlogic bands denser. Image+record `results/geom_review/hi3_GPL1117.{png,json}`; read-only extract unit2686675 EXIT0.
- hi3 now finishes3_4 resize: repair_design inserted136800buffers in125417nets,1275s;2floatingnets advisory shown. No failure/closure verdict yet. Originalroute96GB16threads continues, no patch/restart. Need3_place/DPL, CTSread, GRTTT/overflow, thenr310physicalresult.
- Same E8 lo7 MQ-tail run/container3d1ff8c5dde6 now at fulltopABC15.75. StillSYNTH, notcomplete; don'ttreatoldfailed1024x256netlist asnewresult. Afterterminal check actualu_mq128x23/no1024x256, exact8inventory/PDNprojection, review/resume.
- t6 stage9 minimumphysicalGEN E10 unit3062224-1794896528 EXIT0: `next_t6_stage9_819/gen_stage9_proof1`,60capturedcollectorsmatch. This is privategeometryevidence onoldD3; no route/releaseclaim. MergedMQtailde6d requiredactualt6EL140 too; exact2productionfilepatch deliveredrootforD5bcarry. Stage9rows deliveredC4owner0cycles.
- No existingwholeALLQnativeproductionshapefunctional/throughputbench known; tokenowner notified existingmemory/mechanismcuts doNOT establishALLQruntime. No duplicatebench started.

## CODEX 2026-11-17 00:30 PST — live physical and old diagnostic disposition
- Release hi3 remains original E8 MPL8 container6ffbd6b426e9/unit3543253 in3_5_place_dp diamond legalization, ~22.87/96GiB and active1CPU. Release lo7 remains original MQ-tail container3d1ff8c5dde6/unit4150398 in full-topABC15.75,~27.55/48GiB and active1CPU. No terminal failure, restart, patch or duplicate.
- Read-only declared-input comparison of separate old E8 svcsynth-1115/merge_test_hi4/svc_hi_dsdv_svc_rs__t3 against canonical MPL8: W/merge_test_hi4_input_compare1117.json SHA b162b9c8505311218331039874b9a79f5c1909d847d9457f53287dced080e798. Diagnostic126source inventory3cbc6caffc561f35fdd7a5986c05a5f9e7782b64af75c39ee484f584aff8fee0 vs canonical131source c92a2b39b7ea6dff86ad4ad6e75ec4e9d1dd05ec74d63cc2f4a853e5a8adf1a6; sameH16/D32/NL4 and sevenactive defines, but8source changes +5added fit/capture files, resetcohort differs. Not identical-source vehicle; old contract is superseded. No unique active closure define found; old25% conservativeGPL hook is downstream of synth-only goal.
- Proposed retirement of this superseded diagnostic sent fleet/parent, NOT executed: exact E8 container dpkit-svc_hi_dsdv_svc_rs__t3-3918591; preferred owned ot-run cancel only after unique path-match verification /svcsynth-1115/merge_test_hi4 and source/config/partiallog preservation. Current ABCpid2388357 still live at review. Do not cancel release MPL8/MQ jobs.
- Gunit recovered-view clock inventory is separately READY E10 rows/f2s5_S81-DIE-R/gunit_lib_restore1117/gunit_all7_clock_inventory1117.json, post0656cc8b. Sevenmasters/16instances,15dedicated taps+ordinary l1c; frozen S5g/D5c untouched.

### CODEX hi4 superseded diagnostic retired — 2026-11-17 00:38 PST
- Fleet explicitly authorized owning SVC worker retirement after exact declared-input comparison. Preserved172declared sources/config/inputs/macrolibs/partiallogs15.06MB compressed1.42MB: E8 W/retirement_hi4_1117/declared_inputs_and_partial_logs.tar.gz SHA56986b5c6b2ebefd1c303336f422d516e6cdc95045b0041eb7e09c5b33819cdc. Same evidence copied intel2 ~/s81-cores-r/retirement_hi4_1117. Full original completed objects/source/logs retained in place; no cleanup.
- Reconfirmed exact container ID e6bec27d6c84d2e2754fd16624ccea6260656958c2b58257192cbcec164df843, name dpkit-svc_hi_dsdv_svc_rs__t3-3918591, original merge_test_hi4 /work mount. Exact docker stop returned0; container exited137 then auto-removed. Identity-before, manifest, comparison, stopreceipt and finite docker event trace preserved. This is deliberate retirement of superseded contract, never an elapsed-time stop or equivalent-source pass claim.
- Old container OOMKilled flag was ALREADY true in beforeidentity. Events at retirement show SIGTERM thenSIGKILL/stop/die/destroy, no newOOM event. Do not attribute oldOOMflag to a new capacity failure. Root/fleet/parent notified.
- Canonical hi3MPL8 container6ffbd6b426e9 and lo7MQ3d1ff8c5dde6 confirmedrunning after retirement; no action on either releasejob.

## CODEX PARK — explicit Claude reset, 2026-11-17 00:42+ PST
- PARKED immediately. No new jobs, source edits or terminal waits. Last read00:42: original E8 hi3MPL8 unit3543253-1794880642/container6ffbd6b426e9 in3_5_place_dp, OpenROADpid3070697, CPU100.3%,22.87/96GiB. Original lo7MQ unit4150398-1794884321/container3d1ff8c5dde6 infulltopABC15.75, Yosyspid4165125/ABCpid2914538,CPU100.4%,27.55/48GiB. Both preserved, no terminal result. Next hi3DPL/CTS/GRTTT+overflow; next lo7completednetlist128x23/exact8inventory/PDNprojection/review/resume.
- Delivered minimum t6stage9 GENproof unit3062224 EXIT0 at E10 W/next_t6_stage9_819/gen_stage9_proof1; rows togeometry, currentMQtail sourcecarryrequired. GPL actualreviewPASS-COND image+JSON W/results/geom_review/hi3_GPL1117; no SVCphysicalreadyclaim.
- Other completed handoffs: T51W restoredtuple+measured46rootpacket E7 die-s81-85/t51pin/w_clock_restore_1117/t51w_packet (sharedE/Wtap conflict is geometry/COORD-owned); qualifiedl1c/l2/l4 E7 samebase/gunit_lib_restore_1117; freshGF5BApacket E7 die-s81-85/t51pin/gunit_gf5_recover1117/packet. Seven-master/root coherentinventory E10 s81-b3-clk/rows/f2s5_S81-DIE-R/gunit_lib_restore1117/gunit_all7_clock_inventory1117.json,16instances/15dedicated+ordinaryl1c; l2/l4andBA budgetrows separate, frozenD5cunchanged. Commits0656cc8b(all7),9450fe83(progresscomparison),247aae79(authorizedhi4retirement). Supersededhi4 stopped with smallsource/logevidence at intel2~/s81-cores-r/retirement_hi4_1117; originalcompletedobjects retained. All auxiliariesdone, none left live. No OWNER? newitem.
