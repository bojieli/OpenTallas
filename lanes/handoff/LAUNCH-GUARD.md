# LAUNCH-GUARD handoff (11-23 01:4x PST, Opus)
Lane clone: intel2:/srv/opentallas-scratch2/claude/launch-guard/wt (edits staged from localhost scratchpad wt/, scp'd in).
Files: tools/autopilot/lbl_gate.py (new), kit_wave.py (lbl_launch_refused + same_input_repeat_refused in launch(); private_lbl_refusal in run_item;
pending_row_live in release_pending), autopilot.py (lbl_queue_hold -> WAIT-LBL), noprog_watchdog.py (design_fail_pass, eco_flat_evidence, private kits judged,
UNSIGNABLE first-pass cancel, ot-run --cancel --reason design), tests test_launch_guard.py, test_noprog_design_fail.py, test_noprog_unsignable.py (grace fixture).
Leak paths found: (a) LBL relied on hand holds; hold_records inert on stops_off dies (5 HOLD-LEAK); RETRY-INFRA / FLOW relaunch paths; (b) FIX3: stale
kit_wave_pending.tsv rows (11-05/06, attempt numbers of older events) were permanent pre-release retry keys overriding structural/repeat stops
(c1x_C__t10@3, kv512_C__t1@5, col_h10_r1 cld01bb4ae@11); sle_su_c 28 identical INFRA retries; (c) FIX2: grt_flat skips lane/private kits, gf_cancelled
recorded but container alive never retried, private kits exempt from UNSIGNABLE, ECOs never judged, 30 min grace.
State: focused tests 49 pass; broader subset running; next: ot-push-main, deploy check (rt/current), first-pass count, REPORT to COORD.
WAVE-OPS-R1 told (post 00:54) that LAUNCH-GUARD builds FIX 3.

## 02:2x DONE
main 48869414f4, live rt 6734f6deff0f 01:56. First tick 02:17: 12 LBL refusals. NOPROG 02:00: 7 design-fail units cancelled, scopes verified gone. Lane goal done; watch only.

## 11-23 03:5x
- main feedad5ec7 (rt feedad5ec7e6): FIX 3 hardened (PLACE-SETUP-STOP < -300 ps = design; older design fail not hidden by later cancel/infra attempt) + ENV-EFFECT run_item gate (kit_wave.env_effect_refusal, tools/autopilot/env_effect.py; scan CLI). seqhost/kv512/c1x repeats all launched before 01:56 via stale pending keys.
- Scan 03:4x: 1 mismatch col_h10_r1__t1__cl95b37463__pv1a6ec9c2@2 OT_KEEP_WIRES (stage-resumed kit). MISC kit 1 did have OT_TAP_GRT_PRE=1.

## 11-23 07:37 PST Codex takeover
- Exact reviewed-wave dispatch guard 53a303bb9822, canonical 207/207 GREEN, running in intel2 rt/current 441cd5b7bc9d. User autopilot drop-in zzzzzz-codex-takeover-viewed-route.conf sets AP_REQUIRE_VIEWED_WAVE_ROUTE=1. No service restart or change to running work. Matching exact kit/attempt/build-start minute on enqueue and submit, route below visual wait, generation and placed renders proceed.
- QC obsolete pending E10 V2 slw_fe_v1__clfe325744__cl08d14f0d queue 4ca96043ff34 withdrawn via cfdc0297d83a, AP confirmed. Already-started E2 V2 and E9 V3 survive.
- PHY-B sealed LINT basename-collision correction 8b86009b6f87, canonical 5/5 GREEN, E9 exact GEN_LINT PASS. Wrapper preflight independent structural failure remains held, see TL-QCPHYSDB.

## CODEX notes 2026-11-23 07:46 PST

- Viewed-kit route guard 53a303bb982 GREEN207, merged 441cd5b7bc9, active AP_REQUIRE_VIEWED_WAVE_ROUTE=1 on intel2. No disruption to already submitted units. QC PHY-B obsolete source overlay fixed, exact GEN_LINT green with 8b86009b6f8 (5 canonical files); count-direct archive is hard IP. Legacy exploratory wrapper automatic route stays held. Obsolete exact E10 QC queue item 4ca96043ff34 withdrawn before admission.

## 11-23 08:00 PST
- Retry coverage expanded to finish/CTS/GRT under strict mode in e311d76ce7b, GREEN 41/41, main 7fea07a07a7.
- J8 37 initial GEN/PLACE specs were E8-only because path probing included retired J7 tool-pin metadata. Scoped coord change 5f02d4f53360 removed 395 inactive pins against exact J8 event/bind preconditions. First two new J8 COL specs after cleanup landed E10 and intel1 with all six hosts as roam options and correct runtime 207d4965a0d8. Durable source change d30aabb42ac GREEN 183/183 and READY.
- Strict first live route hold was KV-D28 pv_v5n a3 on E9 at 07:56:55. Viewed image, BAD exact receipt fa8ba5f1974b, runtime read returns WAIT-FORM. Record results/geom_review/kv_d28_pv_v5n_a3_1123.md. Follow D29 PV structural split.
- Two COL HOLD-LEAK alerts are deliberate reviewed J8 probe releases (coord diagnostic 6336eb2f5dad), current explicit holds remain effective. Generic audit unchanged.

## 11-23 09:02 PST

- J8 c3x and c1x t1/t5 exact reviewed structural holds restored after old LBL cron released the mixed prefix at 08:00: e3029da4ada and 1e3d3540335. In-flight placements preserved. Standing helper ed1690a0d0e4b now accepts the exact lbl_family.reason receipt and compares event and hold before removal. 08:30 tick released 0, preserved J9 XGA2 gate.
- Exact terminal watchdog CANCEL-DESIGN rows removed from progress eligibility only, e123566ac21 merged and rt/current. Current false KV 4→0/QC 2→0, real retry candidates remain.
- Exact J8 reviewed E8 t12, t7 cl503f4913 and cl945bc067, t27, and t50 cl39451317 PASS-COND. t20, t44, t7 cl362204c4, t24 cl64811a5d, t29 clc7772371 and t14 BAD. Exact review records and receipts posted. First approved t12/cl503f4913 enqueued at 08:49, BADs transitioned WAIT-FORM.
- Strict newly captured wave GEOM now proposed as placed ODB render with GRT explicitly deferred until exact review, branch 54de977559a6. Focused 57 pass. E10 canonical gate oth-ubuntu-3411249-1795452445 ongoing; inherited active work retains original diagnostic evidence.

## Codex 10:02 PST

- Managed wave render-before-route 54de977559a6 merged 3da0b587bfd; present in the running runtime. New captured geometry runs are static placed-ODB review with GRT deferred. The existing viewer index needs the exact kit and attempt. New private placement probes use goal place and inspect the native render.
- HUNG-WATCH global-place native report fix a7a5a9d13d54, exact E10 source gate 183/183 on c7f9f4bce39, focused 20. Scope oth-ubuntu-715277-1795456256 exit0. KV D28 hub_C report progressed at 09:00:59 despite stdout silence since 07:23, so 09:39 stop was premature. Count only its native report in the existing output clock. Polled exact wave path and direct stage work. No new old form started. Current VIS-COVERAGE DRAFT holds its free retry until D29 strict emit/exact placement. Full evidence and all 26 retired S81 rows in results/kit_wave_3/stuck_state_s81_j7_1123.md.

## Codex fleet snapshot 10:33 PST, 2026-11-23

- Hub and all six build hosts are on runtime `fd1115e442d9` after the 10:33 successful sync. The existing intel2 autopilot drop-in sets `AP_REQUIRE_VIEWED_WAVE_ROUTE=1`. Managed wave route, CTS, GRT, finish and direct retry use the exact viewed kit and attempt receipt in `lanes/GEOM-REVIEW.md`. Newly captured managed geometry dumps and renders actual placed ODB without GRT. Continue private probes at goal place and inspect actual placed renders. Older captured diagnostics and admitted jobs retain their original evidence.
- Native report growth fixes are both active. Global place `a7a5a9d13d54` merged at `242ca80efc50`, canonical 183/183 E10. Placement resizer `15f576b1378` merged at `fd1115e442d9`, canonical 183/183 E9. Only `3_global_place.rpt` and `3_resizer.rpt` count alongside existing logs, with original timeout policy. KV D28 hub_C a4 was stopped prematurely before the first fix, and its free retry is held by VIS-COVERAGE DRAFT until D29 K3 exact placed review. KV D28 PV v12 a3 on E7 has actual resizer report output at 09:46:06 versus stdout at 09:04; normal liveness observation continues.
- J8 current event `891100ef774` plan `6833070df60b`. Its post-apply native elaboration, strict bind and LATCHECK passed (coord `67b82712180`). Of the 48 active-event rows, 15 have exact reviewed OK and live route jobs, 20 have exact viewed BAD and route held, and 13 are still in generation/preflight/place/geometry or held retry. No new signoff yet among those 15 reviewed J8 routes. The inherited, separate J7 station t52 queue `5fab6a0bbcc7` signed 09:57 and archived 09:58 in intel1 `autopilot/closed/s81/slice_station__t52__3c913dbdfb`. The changed J8 t52 exact image remains BAD. The release counter sample at 10:07 counted S81 48/394 types and 72/72 hard-core designs. HEAD count used r17b `18f3c0c7c0c1` with 13/13 pins tables and 25/26 types, 5/5 cores. The stale HEAD board label was corrected in `b7816437a46`.
- Current held forms stay held. All 26 old J7 superseded rows are mapped to named J9 corrections in `results/kit_wave_3/stuck_state_s81_j7_1123.md`. Old J7 LEPW private stopped after definite GRT overflow and copied output back to E10 (ACK `c5aa1d0bd90`). The separate changed J8 LEPW a2 passed KIT_RTL before a generation admission restage to intel1 a3. Latest alert named an old J7 record but current content is J8. Old E7 HEAD east ep3 was stopped by standing UNSIGNABLE-SETUP at 10:30 (ACK `970998aa40e`), with the changed exact east and west probes continuing. Old D28 HGI v8 stopped after GRT overflow 24,595 to 17,047 and copied back to E8, with the separate D29 HK6 diagnostic continuing.
- Repaired E10 Python3.14 renderer in its user site from the exact E9 peer distribution files. Existing files preserved, native `python3 -E` and retained t24 image verified. Historical source corrections cover active-event tool-pin probing, exact J9 structural holds for c1x t1/t5 and c3x, obsolete PHY-B input overlay, and terminal design rows in no-progress detection. One own source gate originally selected E2 scratch2 below the 150 GB takeover floor. That one own scope was stopped and the same gate ran on a healthy host. Existing design/watchdog scopes otherwise remained under their dedicated owners and timers.

| Host | Load / CPUs | Scratch2 free | Scratch3 free | Scratch3 backing |
| --- | ---: | ---: | ---: | --- |
| intel2 hub | 39 / 112 | 270 GB | 93 GB | Root |
| epyc2 | 70 / 128 | 97 GB | 338 GB | Root |
| epyc7 | 94 / 96 | 1,067 GB | 226 GB | Root |
| epyc8 | 76 / 96 | 127 GB | 127 GB | Same NVMe as scratch2 |
| epyc9 | 81 / 96 | 649 GB | 236 GB | Root |
| epyc10 | 96 / 96 | 539 GB | 228 GB | Root |
| intel1 | 79 / 112 | 177 GB | 225 GB | Root |

E8 is below the 150 GB takeover floor. Existing eligible cleanup ran and retained active sources; older expired station paths hit EPERM on root-owned files. The disk-refusal auto-prune still waits for its usual 65 GB threshold. E8 scratch aliases are one filesystem and no E8 scope was manually stopped. E2 scratch2 is below the same threshold. Root-backed scratch3 is only usable on hosts covered by the explicit owner rule with the 150 GB root reserve. Intel1 scratch2 is above the floor with limited headroom. Ordinary timers, admitted CAD and source workers continue.

## Afternoon takeover, 2026-11-23

The hub used `AP_REQUIRE_VIEWED_WAVE_ROUTE=1` on the canonical pinned runtime. New wave placement can render actual ODB geometry before any global routing. Morning inherited t4 and t6 specs predated the static mode and performed their legacy diagnostic GRT after place. Both timed out with overflow unavailable. Their native and actual placements were viewed and marked BAD, and no new route was admitted from them.

- S81 J8 exact actual review BAD for LEPE NH MUS C, LEPW MUS C, and c1x C t3/t4/t5/t6/t8/t10. The pinned native layouts show macro walls, west bank approaches and edge feeders over local capacity, with the long XG and clock paths documented in `results/geom_review/s81_j8_lep_c1x_placements_1429_1123.md`, `s81_j8_c1x_t4_a1_1450_1123.md`, and `s81_j8_c1x_t6_a2_1505_1123.md`. For t6 the actual XG iw[223]→g_d[1226] hop is 1952.48 µm with 16,378 captures over 405 µm, 1,649 collapsed stages, and ft2_o[0] at 360.79 µm. XGA2 owner has the evidence.
- S81 station t12 a2 actual placement passed and its ODB equals the older a1 byte-for-byte. A1 q4f3161e91e03 was already SIGNED and archived as `1d9a20e0debf`. Preserve the duplicate in WAIT-VISUAL without an authorization that would route the same checkpoint again. Its report is `results/geom_review/s81_j8_slice_station_t12_a2_1433_1123.md`. Stale ENQUEUED/RUNNING cache had let the ghost reaper cancel the archived a1 before follow_queue. Branch `7a15228190e` prevents that exact race, tested 184/184 again on ed4f6ade31b after gate drift.
- KV owner viewed D28 v12 a3 BAD and QC owner viewed TTCTLM a3 BAD and native59 a2 OK. All three canonical entries are recognized. Only native59 entered a new route, q1f5b9e4e4c0e. HBM remains parked and the false pre-tick missing-plan notice is cleared after using canonical adoption guard (merged `b4e3e9f1183`). The old hook is retained as `intel2:~/bin/adopt-guard-pretick.sh.pre-rt-1123`.
- All seven exact stale submissions with no kit path or live job were withdrawn append-only at `c648581a8d2b`: 1088e6be0ffe, 1a5a2055e90b, 1aab0723acde, 588b1e5cbeb2, df462e10f94c, f1df43e9e6c1, b7e3f038d850. The next tick read all seven as WITHDRAWN. The legitimate spare tag retry now runs and takes several minutes with zero promotions. This ancillary optimization was deferred.
- AGIdock and rtx INDEX receipts confirm seven J8 R-MINIMAL station records, each DRC 0 and antennas 0. The records are t24 `76c642e70a40`, t47 `0365813807cc`, t6 `ed2d2795bb39` and `457e38657399`, t7 `9cfe2b7b2203` and `54ebc954a5e6`, and t12 a1 `1d9a20e0debf`. TT setup spans +12.20 to +144.14 ps. The archive marks outstanding port-start FF qualification at the actual parent.
- Recovered E7 QC `c1f811ac6204`: retired source ECO paths prevented rtx tar. The authoritative retained closed copy matched all eight hashes, so only the input file locations were reconciled under the ordinary export lock. Full rtx transfer completed 15:22:52 and both INDEX rows were posted 15:25. E10 `e18cf5c71334` independently exported both. Fresh QC `6137069a3ab6`, `428df61a733b`, and `29f5bc026b7c` are normal new export work.
- Old epyc10 HEAD e-shim a3 q3054c87a89d6 had 39 archive failures because the original kit no longer exists anywhere on the active fleet. Its exact status is now SIGNED-NOT-ARCHIVED, with prior signoff history retained, after `becebaf53d9`. Distinct HEAD NF15f r3 archive `d97e00318602` remains the actual closure.
- Source `67466974548` reports exact native DRT no-progress above the generic Killed wrapper line. E8 D27d3 HROOT stopped itself after 20 iterations with 24,261 markers. Source `ca72436ff1e` reports the terminal KLayout missing GDS/OAS cell instead of the earlier caught RSZ cap. Old S81 H9R0 P1 pv697f40c9 got through native 5_2 and 6_report before 17 missing hard-cell GDS/OAS views, and retained DRT 28, TT 1,592 and hold 619 violations. Preserve its final ODB/DEF/SPEF. E7 old J7 KV512 t1 retains GRT-0116 overflow 5,122,715. E8 old D28 hub_C and E10 old QC COL core scopes were retired by their standing GRT-0273 watchdog after flat overflow. The E9 old PCv3 pair is report-only and remains live per KV owner, CPU-active in the all-path FF repair with +5 ps previous pass and obsolete TT -752/-591.
- Observer `9225a8506c5` deployed and suppresses a stale event-pending log marker only when its matching live config is gone. S81 NO-LAUNCH reflects deliberate J8 family holds and place/route states. The 26 superseded rows are accounted under `results/kit_wave_3/stuck_state_s81_j7_1123.md`. No withdrawn approved form or inherited scope was manually stopped.
- Routed viewer pack dispatch was repaired at `ed4f6ade31b` to declare exact ODB and renderer sources, and retain the originating host for publication. The latest native t47 layout export is on epyc8 `oth-ubuntu-3229126-1795475636`, with hub wrapper `launch-guard-viewpack-t47-1514.service`, hub log `launch-guard/tmp/viewpack_t47_1514/worker.log`, and E8 log `explorer-store-r1/tmp/auto/s81.t.slice_station__t47.log` under scratch2. Prior viewer aliases for the other six are older from the previous closure. Existing budgets stayed in place for historical failed pack requests.
- COL EW p3/p5 exact I1 work uses `s81-col-j9/ew1_place_1438/launch.log`, unit `s81-col-j9-ew1-place-1438.service`, and strict bind scope `oth-ubuntu-4168133-1795473449`. Plan `d38f42da603e`, Wave-A asbuilt `555d3793bb64`, runtime `ba57ce0e0288`. Recovered the absent config as an explicit captured input. The inherited finish recipe remains unused. The supervisor generates only two `goal=place` specs after strict pass, and each needs actual image review before any downstream route.
- Parallel guarded cleanup is healthy. Secondary autoclean I1/E2 sticky safety alerts remain set because it saw protected HEAD/HBM paths. E7/E10 are fail-closed on stale snapshots because the distributor could not overwrite identical owner-read-only installed tool files. Recovery was deferred. E2 true scratch2 remains below the floor and only its owner-authorized root-backed scratch3 is eligible with its independent 150 GB root reserve.

The 15:29 sample had the hub and all six gen hosts on `bd54869e80c5`, including the ghost correction merged as `d0beea9d604`. Current J8 wave has six signed rows and eight exact reviewed routes in progress. Of 30 route-held rows, t12 a2 is the only intentionally unmatched visual receipt. Three I1 inherited place attempts remain in progress, and c1x t1 keeps its deliberate XGA2 preflight hold. Strict EW preflight still ran and emitted fresh per-type TAP advisories at 15:26. At 15:27 the t47 native OpenROAD extractor was admitted and active, with publication pending.

| Host | Load / cores | True scratch2 free | Root free |
|---|---:|---:|---:|
| intel2 hub | 35 / 112 | 214 GB | 93 GB |
| intel1 | 56 / 112 | 249 GB | 350 GB |
| epyc2 | 38 / 128 | 79 GB | 742 GB |
| epyc7 | 56 / 96 | 981 GB | 226 GB |
| epyc8 | 91 / 96 | 550 GB | 246 GB |
| epyc9 | 64 / 96 | 494 GB | 227 GB |
| epyc10 | 35 / 96 | 192 GB | 236 GB |

The E10 scratch2 trend postponed extra low-priority viewer packs. E7 cap expiry was reported alongside ordinary admission, with the loaded policy unchanged. The primary dispatch, export and farm watcher schedules remain active.

The 15:35 update confirms all five QC export records `c1f811ac6204`, `e18cf5c71334`, `6137069a3ab6`, `428df61a733b`, and `29f5bc026b7c` are DONE in the export ledger. The restored EW p3/p5 PRE passed with receipt `4e541f7bfd42` and the same scope advanced to ELAB. The 15:32 hold audit was all zero. Standing watchdogs retired old I1 D28 PV v3e and the remaining old E10 COL core after flat GRT-0273. They retained the kits. A separate E9 old PV v4 has an UNSIGNABLE notice at TT −368.67 ps and an ordinary 16:00 watchdog decision unless the owner keeps it.

At reset, the E8 t47 extractor had inventoried 1,903,223 wire rectangles, 5,331,434 vias and 5,837,831 instances. Its working directory had grown to 3.3 GB and publication remains pending in the admitted scope. I1 EW continues in ELAB with the exact PRE receipt above. E7 old `slw_fe_v2__clf110fab2` q`b3f830d6c9f7` ended with external SIGTERM after the native detail optimizer was still at five violations. Standing flat-five notices preceded it and the precise issuer is unconfirmed. The old R7 I1 v3e stopped scope was the sole spill of E10 original `kv3_pv_v3e_1122231609`, as proven by hub spec `_1122231648/chain_a1.live.log`. The separate E10 old R7 v3 remained CPU-active in the repeated final FF hold loop and remains an owner report-only scope. All admitted jobs and schedules were left running.
