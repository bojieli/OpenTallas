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
