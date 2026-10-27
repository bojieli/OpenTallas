# RC/canary interim packet — 2026-10-27 10:06 PDT

This is an interim packet, not a park/reset. Continue collection until the explicit reset notice.

## Source and integration

- Combined candidate: `codex/rc-canary-1027@ab3ae7c3ab8a` = RC2bbe885e4/7944d7dae + shared placement60um37d9b8a28 + preflightb56b0b55be (includes FF-bound9529b56ff0) + core-pin-snap5b2b94251f. Global RC/60 promotion remains HELD on QC regression.
- Evidence: `codex/rc-evidence-1027@6c4b5b78b`, all seven actual placement reviews, exact5b review, QC control trial review, static qualification and exact QC input/path diagnosis under `results/{geom_review/codex_rc_canary_1027,flow_rc_1027}`.
- Separate committed/pushed helper fixes (ROOT owns integration): `codex/flow-watch-1027@3400e5da8` explicit five shared Python dependencies + dry-submit fixture repair (33 tests); tip `e0fbdbc0f` adds explicit adder-map watch (6 watch tests). `codex/hbm-lint-1027@53db0772b` copies/runs RTL lint before HBM synthesis (4 tests+bash-n). `codex/map-mtime-1027@18a1048a4` preserves unchanged generated mapper mtime (5 tests). No active kit was modified for these fixes.

## Nine reference/trial records

| Record | Exact source | State / relative result |
|---|---|---|
| hbm_ab3ae7c3a_1027_081901_659397 | ab3ae7c3ab8a | active |
| hbm_sram_ab3ae7c3a_1027_081901_659397 | ab3ae7c3ab8a | NO-REGRESSION |
| qwen_compute_ab3ae7c3a_1027_081901_659397 | ab3ae7c3ab8a | REGRESSION |
| qwen_kvsys_ab3ae7c3a_1027_081901_659397 | ab3ae7c3ab8a | NO-REGRESSION |
| qwen_kvsys_core_ab3ae7c3a_1027_081901_659397 | ab3ae7c3ab8a | active |
| s81_ab3ae7c3a_1027_081901_659397 | ab3ae7c3ab8a | active |
| s81_head_ab3ae7c3a_1027_081901_659397 | ab3ae7c3ab8a | NO-REGRESSION |
| qwen_compute_7fd3cec6d_1027_093146_950078 | 7fd3cec6d876 | active |
| s81_5b2b94251_1027_084224_600035 | 5b2b94251fc5 | active |

## Active jobs: supervisor host intel2

Use the client unit below; `otrun.log` identifies the actual ot-run worker if it spilled. Each directory contains `canary_meta.json` and eventually `canary.json`. Initial placement-only FAIL receipts remain separately preserved under the respective `runs/` roots.
- `codex-canary-route-hbm-ab3ae7c3a` — `/srv/opentallas-scratch2/claude/codex-rc-canary-1027/ab/final/hbm_ab3ae7c3a_1027_081901_659397`
- `codex-canary-route-qwen-kvsys-core-ab3ae7c3a` — `/srv/opentallas-scratch2/claude/codex-rc-canary-1027/ab/final/qwen_kvsys_core_ab3ae7c3a_1027_081901_659397`
- `codex-canary-route-s81-ab3ae7c3a` — `/srv/opentallas-scratch2/claude/codex-rc-canary-1027/ab/final/s81_ab3ae7c3a_1027_081901_659397`
- `codex-canary-route-qwen-compute-ctl40-c60-7fd3cec6d` — `/srv/opentallas-scratch2/claude/codex-rc-canary-1027/qc_ctltrial/final/qwen_compute_7fd3cec6d_1027_093146_950078`
- `codex-canary-route-s81-exact5b2b94251` — `/srv/opentallas-scratch2/claude/flow-canary/runs/s81_5b2b94251_1027_084224_600035`

Fast read-only collection:
```sh
ssh intel2 python3 /srv/opentallas-scratch2/claude/codex-rc-canary-1027/status.py
```

## Results, failures and next steps

- Combined HBMSRAM, HEAD and KV type: NO-REGRESSION, with inherited absolute design/insertion stops retained; no physical sign-off claimed. QC: REGRESSION, FF hold−197.06 vs−167.66ps,2320vs2324 endpoints. Old4CTS+newRC changes slack only0.002ps; new capture path adds three CTS stages/+29.57ps while data arrival stays~175.6ps. PreCTS old/new both have direct root clock `clk`,9164 loads; the60um hook did not directly modify the clock.
- Exact used QC plan is SHA256`54a1aeb5065d061a14e15a838e491b5f24975530a655e1c3eafb99f22ace4e9f`, identical in gitab3 and gita54. Its coll_ftm.clock omits control_sinks; generated kit has21 generic taps and u_run_in lands on far clk_t18. Full path/hash/control-hook/assignment trace: `results/flow_rc_1027/qc_regression/used_input.json`.
- The existing ONE-QC candidate100 already has modern control_sinks+sender40. ROOT approved ONE isolated changed-profile trial from pinned `codex/qc-ctltrial-1027@7fd3cec6d876`, cloning its concrete generated kit rather than regenerating inputs. All nine pre-floorplan stages PASS; actual reset/run DFFs are~9.3/10.9um from clk_t13[768.464,918.112], PG348258terms/0open. Qwen and CODEX viewed actual placement PASS-COND. Its continuation is diagnostic only: no comparison/NO-REGRESSION claim against the old canonical reference, and no production AP/type hold bypass.
- Exact5b S81 canonical canary source`5b2b94251fc5` was separately ROOT-approved for three fixed-core trials. Actual placement was reviewed before continuation. The t12 reference contains no12.7core slice, so the snap mechanism remains covered by96tests plus the core owner actual probe, not by this canary. On terminal verdict notify `/root/s81_head/s81_core` (current L1c row a21dca78883e supersedes448245f79f4f; qbank/sstn remain held). Never misattribute the combinedab3 cohort to exact5b.
- Resuming the existing wrappers repeated synthesis/placement because adder_map_dontuse.v was rewritten with identical bytes and a new mtime; they also repeat LEC. The18a1048a4 fix prevents the mapper invalidation for future kits. Current jobs were not restarted or patched.
- Seven-kit static qualification preserved5PASS/2FAIL. Four gen_phys samples have actual pre-Docker KIT_PREFLIGHT PASS markers; three core checks were explicitly post-admission qualification. Both HBM failures were exactly missingrtl_lint.py; source fix53db0772b corrects packaging and the standalone pre-synthesis call. Existing candidate kits/failures were not patched to force PASS.
- Collected separate canonical legacy KV core source0f978: `.../flow-canary/runs/qwen_kvsys_core_0f9789993_1027_043154_799814/gen/kv3_head_eighth_e1__216x216/signoff_hold/signoff.json` is SIGNED, TT+12.02/FF+2.93ps, both SPEF, no reasons. Qwen owns current-plan interface/slice/routed-LEC qualification and preservation; this does not establish native-plan closure.
- Applied the already ruled KV type constraint rebaseline only to hold_ff_wns/ep (−94.57ps/2213), preserving old3352 in `.pre-5ca97-1027`, prior insertion/overflow/DRV metrics, and every tolerance. No failed original verdict was overwritten.
- Inherited canonical HBM8810 is genuinely progressing in long GRT port-hold repair (09:15 iter2110,10016data buffers,+3.3%, WNS−115.19/TNS−68.3ns), not a deadlock. Manual S81b458 had no client_unit but a live Docker/run PID40754 when diagnosed; do not classify it as orphan or retry without liveness collection.

## Source protection and operator helpers

- Locked immutable source worktrees on intel2: `/srv/opentallas-scratch2/claude/wt/codex-rc-canary-1027` (ab3), `codex-exact5b-canary-1027` (5b), `codex-qc-ctltrial-canary-1027` (7fd). Do not update/remove them while clients reference them. Unlock/remove only once all referencing verdicts and client units are terminal.
- Operator scripts under intel2:`/srv/opentallas-scratch2/claude/codex-rc-canary-1027/`: `status.py`, `dump.py`, `dump_exact.py`, `dump_place.tcl`, `rend.py`, `resume.py`, `resume_exact.py`, `resume_ctltrial.py`. All desired continuations already started; resume scripts refuse duplicate final directories. No polling daemon or job cancellation was added.
- Keep current clock/hold/insertion gates unchanged. Do not blanket loosen target-band checks from old failing reference kits; only escalate a concrete otherwise-valid current core with its explicit clock-binding/IO contract.

OWNER? None.

## CODEX 10:09 collection update
Combined S81 ab3 is now terminal NO-REGRESSION: insertion TT224.30/FF180.66ps vs226.54/183.35; FF hold−81.96ps/691EP vs−76.73/691, overflow0/DRV0. Absolute insertion gate remains FAIL (deviation25.70/21.84ps vs20ps); no physical signoff. Combined cohort now4NO-REGRESSION,1QC REGRESSION,2active. Four active total including exact5b andQCtrial. Exact5b progresses GRT hold iter760/1379buffers, WNS−30.772ps/TNS−5379.527ps; QC7fd GRT setup repair586EP/WNS−11.441ps; HBMab3 GRT holditer780/WNS−240.638ps; KVcoreab3 CTS holditer6520/7066buffers,WNS−80.701ps. No new jobs or active-kit mutations.

## Handoff to Claude 2026-10-27 10:14 PDT — FLOW-RC/FLOW-CANARY
Explicit reset received via root/flow. Safely parked; no half-written source, new job, baseline edit, kill or rerun. Complete packet: handoff/codex_rc_canary_20261027_1006.md. Source RC60 cohort codex/rc-canary-1027@ab3ae7c3ab8a remains HELD; exact5b source5b2b94251fc5; controlledQC source7fd3cec6d876. Evidence codex/rc-evidence-1027@6c4b5b78b. READY independent helpers: codex/flow-watch-1027@e0fbdbc0f, codex/hbm-lint-1027@53db0772b, codex/map-mtime-1027@18a1048a4; parent/root own integration (no merge claim here).
Final nine-record collection: combined ab3 HBM_SRAM, HEAD, KVtype, S81 = NO-REGRESSION but absolute reference design stops/no signoff; QC = REGRESSION FF−197.06 vs−167.66ps. Combined HBM/KVcore active, exact5b S81 active, QC7fd controltrial active. QC cause: unchanged data path and~0.002ps RC estimate difference, placement/CTS capture adds3stages/+29.57ps; exact used plan lacks control_sinks; changed-profile7fd active with corrected dedicatedclk_t13 controls9.3/10.9um. No baseline weakening; oldreceipts preserved. LatestS81ab3 insertionTT224.30/FF180.66,hold−81.96/691EP; inherited insertion dev25.70/21.84>20 stop.
Four active supervisor units on intel2, paths:
- codex-canary-route-hbm-ab3ae7c3a: /srv/opentallas-scratch2/claude/codex-rc-canary-1027/ab/final/hbm_ab3ae7c3a_1027_081901_659397
- codex-canary-route-qwen-kvsys-core-ab3ae7c3a: /srv/opentallas-scratch2/claude/codex-rc-canary-1027/ab/final/qwen_kvsys_core_ab3ae7c3a_1027_081901_659397
- codex-canary-route-qwen-compute-ctl40-c60-7fd3cec6d: /srv/opentallas-scratch2/claude/codex-rc-canary-1027/qc_ctltrial/final/qwen_compute_7fd3cec6d_1027_093146_950078
- codex-canary-route-s81-exact5b2b94251: /srv/opentallas-scratch2/claude/flow-canary/runs/s81_5b2b94251_1027_084224_600035
Check allnine: ssh intel2 python3 /srv/opentallas-scratch2/claude/codex-rc-canary-1027/status.py. Read otrun.log for workerunit; no duplicate continuation. Notify S81coreowner exact5b verdict and Qwen controlledtrial terminal promptly. Keep three locked fleet source worktrees until allreferences terminal; manual cleanup only after. All original receipt failures retained. OWNER? None from this lane.
