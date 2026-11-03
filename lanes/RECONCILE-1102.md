# RECONCILE-1102: map of Codex live jobs and results (Codex covered 11-01 20:34 to 11-02 08:24 with no handback; out until 11-08)
Updated 2026-11-02 18:54 PST by lane RECONCILE-1102 (Claude). Sources: ~/coord/handoff/codex_checkpoint_20261102_0158.md and its directory, lanes/CODEX.md, CODEX-LOG >9783, CODEX: lines in HANDOFF.md, and live probes of every oth- user scope, docker container and ot-heavy completion record on intel1, intel2 and epyc2 (40 Codex units live at 17:57). Read-only except for the watchdog stops in section 2. Codex's dirty ~/coord files were not touched.

## 0. Summary for owning lanes. These results are collected: do NOT rerun them
- **Hung jobs stopped by the 2-h watchdog (section 2):** W1 S81 whole-KV bridge SYNTH (15 h in the Yosys SHARE pass), W2 QC frozen clock source-kit4 (13 h without output), W3 KV norecipe qkd_hr_core_prompt EQ (20 h). Another lane had already ended the kvpeer EQ x3 and the HBM gql_d26 finish x2 (exit 137) at about 18:38.
- **Local ot-run clients:**
  - 531391 = W1, now exited 137.
  - 793327 = epyc2 oth-ubuntu-3134028 kv3_pc place r5. PLACE already FAILED on cell cap 903118 > 400k; only the sidecar LEC is alive (DIE-KV-61 may stop it).
  - 1164733 = intel1 oth-ubuntu-1620213 HBM ROOT clock batch resume, RUNNING and progressing (MOVE 162, metric 0/0/12; DIE-HBM-58).
- **Kit-wave failure classes for KW-FIX-1:**
  - (a) CELL CAP: 6 S81 serdes kits and KV kv3_hub_Eo/Wo, PLACE >400k cells (461k-578k). This needs a split or partition, not a rerun.
  - (b) QC kit PLACE GPL loop: 12 units looping 16-20 h, with overflow stuck at 0.37-0.51, about 50% fixed instances and util about 4.5%. Units: epyc2 2605092, 2668568, 2725425, 754384 (plus non-Codex 1901899); intel2 1195910, 1729100, 1824717, 1866958, 1890997, 2061954, 2188293, 43405. One class fix covers all of them (outline/util or fixed-instance cause); then relaunch as a batch.
  - (c) QC geom_check GRT: about 55 min per iteration with clock nets routed as signal. Units: intel2 1070367, 1426550, 2126004, 1624527 (silent 3 h 15 m, so hung by the rule and referred, not stopped), 2852744.
  - (d) HEAD 94510 wave units finished but the ledger says RUNNING: run collect() under kit_wave.lock.
  - (e) S81 T41/T51 ledger rows disagree with the units.
- **Uncollected terminals Codex never reported (now collected here):**
  - HBM: L9m FT joint PASS (14 slots, max hop 405.00); DRT readouts NW_v1/NE_v1 PASS; HCOL565 h0/h1 r3 LEC NOT_EQ (117/16 differences, err[1] class); StoreA regional4 UNPROVEN (128 X points); programme current-0905 EQ; Tnode fill-prep 0910 exit 2.
  - KV: AHUB maxwire80 TT +22.51 / FF +5.42 / DRV 0, blocked only by the unexpanded child ETM clock; HG9 q1 LEC EQUIVALENT 19533/19533; PC dataGRT PASS (GRT0, PG 0 fail; DRT successor already launched by a Claude lane); TT_C rowprep v4/v5 INFEASIBLE.
  - QC: L1 DRT FAILED (no LVTN filler).
- **SIGNED and waiting for merge plus count:** PV B w80 (TT +51.16 / FF +10.36, DRV/DRC/ANT 0, EQ 18181/18181), READY 6f1ba3b70 (codex/pv-export-reader-0405). Goes to ROOT-MERGE-22 / SIGNOFF-SPRINT-21.
- **READY not on main:** 77 Codex branches (section 4) posted as ONE READY batch for ROOT-MERGE-22. 8 of them CONFLICT.
- **OWNER? questions:** 30 since 20:34. 17 are covered by COORD/OWNER rulings; 13 are OPEN and routed to their die lanes with defaults (section 5).

## 2. Watchdog stops (OWNER 12.22 2-h hung-job rule), recorded BEFORE stopping, 2026-11-02 18:41 PST
| # | host | unit | container / pids | started | last output | evidence | reason |
|---|---|---|---|---|---|---|---|
| W1 | intel2 | oth-ubuntu-1159241-1793599785 (local ot-run client pid 531391 on coordinator) | docker codex-kvbridge-size-2111-1181066 (100% CPU, 24.1/32 GiB) | 11-01 21:56 | 1_2_yosys.log 11-02 03:28 (15 h 12 m ago), last line "3.15. Executing SHARE pass (SAT-based resource sharing)" | /srv/opentallas-scratch2/claude/codex-s81-kvbridge-size-2111/run/logs/asap7/kvbridge_size_2111/base/1_2_yosys.log; no mapped netlist | Yosys SAT SHARE pass with no output >2 h (15 h): hung. Successor (DIE-S81-48): rerun SYNTH-only with the yosys SAT 'share' pass skipped (resource-sharing off), same 32 GB/8T |
| W2 | intel1 | oth-ubuntu-856593-1793624595 | python die_trial.py kit workers pids 1080851/1080852 (97% CPU each, RSS 4.4/4.3 GB, 13 h CPU) | 11-02 05:03 | emitted4/kit/abstracts/*.lef 05:14 (13 h 26 m ago); source_kit4.log and emitted4/kit.log empty (0 B); no source_kit4.rc | /srv/opentallas-scratch2/claude/codex-qc62-clock-frozen-source-1102 (ot_clk kit config4.yaml, check4 PASS) | No file/log output >2 h (13 h) while computing: hung by the 2-h rule. Successor (DIE-QC-63): rerun 'ot_clk.py kit' with logging/--workers 1 on the current QC plan (the job used the frozen 1101 plan; DIE-QC-63 G0C/plan class has moved since) |
| W3 | intel1 | oth-ubuntu-783823-1793547550 | docker codex-kvfp-qkd_hr_core_prompt (2 yosys equiv procs at ~200% CPU, 1.2 GiB) | 11-01 07:42 | eq_post.log/eq_mut.log 11-01 22:06 (20 h 40 m ago), both stopped mid-ezsat on u_core.hc[177]; eq_v rc 0 (2712 s) | /srv/opentallas-scratch2/claude/codex-kv-norecipe-1101/jobs/qkd_hr_core_prompt/fp/qkd_hr_core_prompt/ | No log output >2 h (20 h), and no Codex note after 11-01 mentions it (orphaned). eq_v PASS is kept. Successor (DIE-KV-61): run the post/mut EQ with the induction/ezsat hint set (the same recipe as the HG9 q1 proof), or treat it as a structural-LEC class |

Already ended before my check (exit 137 at about 18:38, stopped by another lane, not by me): intel1 kvpeer EQ alias2 oth-ubuntu-1250079-1793541520, alias-unkept oth-ubuntu-1751467-1793541773 and nogroup oth-ubuntu-737955-1793540880 (no verdict; eq_v logs 22-24 h stale); intel1 gql_d26 finish oth-ubuntu-77895-1793345168 (7e7e2a, DRT opt iter 58, 565 viol, log stale since 11-01 19:37) and oth-ubuntu-77929-1793345168 (068dba, iter 58, 454 viol, stale since 11-02 00:14). Both units are inactive with no completion record.

Hung by the rule but NOT stopped (an active lane owns the class): intel2 oth-ubuntu-1624527-1793601346 QC geom GRT slw_fw_v1, grt.log 15:31, extra iteration 19/50, 3 h 15 m silent. The QC kit-wave failure-class lane is inspecting the hung geom_check GRT containers, so it is referred to KW-FIX-1 / that lane.

## 3. Job table by lane group (state checked 18:0x-18:47 PST; result paths are on the host named)

### A. FLOW / kit-wave / PG-birth / S81 source (subagent FLOW, checked 18:0x-18:3x)
| job | host | unit / container | path | state | result | owner | note |
|---|---|---|---|---|---|---|---|
| T7 native GEN_LINT canary svc_lo_dsdv_svc_rs__t7 | intel1 | oth-ubuntu-80731-1793597049 | scratch2/claude/codex-flow-s81-source-2055/t7_current_canary2/gen/svc_lo_dsdv_svc_rs__t7/gen_lint.json | FAILED exit1 11-02 03:57 | gen_lint FAIL: 9 memory-cap issues (memory_bits) | DIE-S81-48 | needs macro-memory specialization; do not rerun as-is |
| S81 kit serdes__t1__clb45db5be a2 | intel1 | oth-ubuntu-2579467-1793603371 / dpkit-serdes__t1__clb45db5be-1413559 | scratch2/claude/codex-s81-wave-1345/kit-wave/s81/b1a2125433d0/items/serdes__t1__clb45db5be/attempt_2 | RUNNING (LEC only) | PLACE FAIL cell cap 477,022 > 400k; async LEC hyp1 16:41 | KW-FIX-1 | cell-cap CLASS: kit cannot pass; container alive only for LEC |
| S81 kit serdes__t4 a2 | intel1 | oth-ubuntu-1419901-1793601999 / dpkit-serdes__t4-1551087 | .../items/serdes__t4/attempt_2 | RUNNING (LEC only) | PLACE FAIL 500,092 > 400k; LEC rawbase3 18:04 | KW-FIX-1 | cell-cap class |
| S81 kit serdes__t12 a2 | intel1 | oth-ubuntu-2533102-1793603239 / dpkit-serdes__t12-3977201 | .../items/serdes__t12/attempt_2 | RUNNING (LEC only) | PLACE FAIL 461,354 > 400k; LEC hyp0 17:33 | KW-FIX-1 | cell-cap class |
| S81 kit serdes__t14 a4 | intel1 | oth-ubuntu-1523371-1793602292 / dpkit-serdes__t14-2139207 | .../items/serdes__t14/attempt_4 | RUNNING (LEC only) | PLACE FAIL 460,465 > 400k; LEC hyp5 17:52 (15 h, all hyps failing) | KW-FIX-1 | cell-cap class |
| S81 kit serdes__t15__cla2127225 a3 | intel1 | oth-ubuntu-3967074-1793607685 / dpkit-serdes__t15__cla2127225-3857836 | .../items/serdes__t15__cla2127225/attempt_3 | RUNNING (LEC only) | PLACE FAIL 505,600 > 400k; LEC hyp4 17:57 | KW-FIX-1 | cell-cap class |
| S81 kit serdes__t15__cla3d02796 a2 | intel1 | oth-ubuntu-4050320-1793607941 / dpkit-serdes__t15__cla3d02796-4052205 | .../items/serdes__t15__cla3d02796/attempt_2 | RUNNING (LEC only) | PLACE FAIL 540,550 > 400k; LEC hyp0 17:14 | KW-FIX-1 | cell-cap class |
| KV kit kv3_hub_Eo a3 | intel1 | oth-ubuntu-1172687-1793601156 / dpkit-kv3_hub_Eo-3944761 | scratch2/claude/codex-kv-wave-1131/kit-wave/qwen_kvsys/event28w_c/items/kv3_hub_Eo/attempt_3 | RUNNING (LEC only) | PLACE FAIL 577,883 > 400k; LEC hyp21 18:04 | KW-FIX-1 | cell-cap class |
| KV kit kv3_hub_Wo a3 | intel1 | oth-ubuntu-1531057-1793602304 (container gone) | .../items/kv3_hub_Wo/attempt_3/gen/kv3_hub_Wo/{FAIL_PREFLOOR,lec_run.log} | FAILED exit5 18:00 | PLACE FAIL 597,550 > 400k; LEC KEEP FAIL 200,178/200,212 proved, 34 differ (11 kept bits merged/renamed u_astk_WN.m3/m4.zq[7:9]) | KW-FIX-1 | 2 classes: cell cap + KEEP/rename |
| geom_check kv3_sys_SD a4 GRT | intel1 | oth-ubuntu-2092896-1793628988 / ap-ageom-kw-kv3-sys-SD-grt-2296992 | .../items/kv3_sys_SD/attempt_4/geom/grt.log | RUNNING slow (log 18:02) | GRT extra iteration 41/50, 11 h 46 m | GEOM-110 | not hung |
| S39 ELAB fresh | intel2 | oth-ubuntu-1330463-1793600396 | scratch2/claude/codex-flow-s81-source-2055 (=R) | FINISHED exit2 | ELAB PASS 245 modules/0 undefined; exit2 = stale dead-proof guard | DIE-S81-48 | |
| S39 BIND clk28r2 | intel2 | oth-ubuntu-799024-1793607555 | R | FAILED exit1 | t18 radius 151.093 > 150 | DIE-S81-48 | superseded |
| S39 all-gaps clock census | intel2 | oth-ubuntu-1540548-1793609824 | R/clock_census_all/CENSUS.json | FINISHED exit1 | only error t18 | DIE-S81-48 | |
| S39 clock supplement17 r2 | intel2 | oth-ubuntu-2912251-1793613975 | R/clock_supplement17_r2 | FINISHED exit0 | found cl911 t28 radius 219 > 200 | DIE-S81-48 | |
| S39 final BIND clockset r2 | intel2 | oth-ubuntu-3259882-1793614902 | R/bind_final_clockset_r2 | FAILED exit1 | only t49 clk_t25 150.963 > 150 | DIE-S81-48 | |
| S39 all-168 budget census | intel2 | oth-ubuntu-1006604-1793619280 | R | FINISHED exit0 | 167 PASS, t49 fail | DIE-S81-48 | |
| S39 t49 BIND successor | intel2 | oth-ubuntu-1252503-1793620193 | R | FINISHED exit0 | BIND PASS 398 parts/204 types/873 crossings/0 errors | DIE-S81-48 | physical reset-halo HOLD remains |
| S39 frozen gen latency | intel2 | oth-ubuntu-4063849-1793631188 | src/results/flow/source39_inactive_event_0740 | FINISHED exit0 | 873 cycles unchanged, digest bbec1f44f3672842 | DIE-S81-48 | |
| S39 source-event capsule assembly | intel2 | oth-ubuntu-167016-1793632342 (ctl codex-flow-s39-capsule-0800) | R/capsule_0800.client.log, R/source_event_capsule_0800 | FAILED exit2 ~07:17 | tar "Cannot unlink: Directory not empty" in overlay step | FLOW-22 | Codex 08:xx called it running: WRONG. Fix tar overlay, rerun once |
| HEAD R3 native label restore | epyc2 | oth-ubuntu-4053634-1793609824 | scratch2/claude/codex-head-native-lemma-r3-1102 | FINISHED exit0 | 12 PASS/16 rejected (diagnostic) | DIE-HEAD-54 | |
| HEAD typed70 native | epyc2 | oth-ubuntu-1829744-1793619407 | scratch2/claude/codex-head-typed70-0248 | FINISHED exit0 | 98/98 joint outputs PROVED (056966c11) | DIE-HEAD-54 | |
| HEAD LA2 native | intel1 | oth-ubuntu-3866190-1793636171 | scratch2/claude/codex-head-la2-0940 | FINISHED exit0 | 238/256 proved, 18 p_take left (9986995ad) | DIE-HEAD-54 | |
| HEAD p_take45 r1 / r2 | intel1 | oth-ubuntu-255411-1793638595 / oth-ubuntu-270248-1793638655 | scratch2/claude/codex-head-ptake45-r2-1030 | r1 FAILED (missing aig), r2 FINISHED exit0 | 45/45 + 90 aux PROVED; 455/469 residuals closed, 14 padding left (77071ae92) | DIE-HEAD-54 | padding = WTX item (preservation fragment 69812606f) |
| ECO hd_st_n4 pilot | intel2 | eco_loop pid 796908 | scratch2/claude/kw-eco-1/pilot/hd_st_n4/eco_20261101_215110_796908/eco_loop.json | FINISHED 15:54 | EXHAUSTED 3 iter: base TT146.24/FF-2.06/DRV3824 -> best TT141.57/FF+7.84/DRV33 (12 TT/21 FF), DRC0, NOT SIGNED | KW-FIX-1 (HEAD-54 informed) | only DRV left |
| ECO hd_st_m / idxqs pilots | intel2 | eco_20261101_211115_4063922 / eco_20261101_221056_1180178 | kw-eco-1/pilot | FINISHED | EXHAUSTED: hd_st_m TT111.10/FF7.21/DRV1; idxqs TT-54.43 | KW-FIX-1 | |
| HBM hfdep K40 a2 | intel2 | oth-ubuntu-1656101-1793601436 | hbm-cores-kits-40/hfdep/a2_gen | FAILED exit6 | ModuleNotFoundError core_clock_band (post-CTS) | DIE-HBM-58 | tool-path class |
| L4 AFTER-DRV checkpoint | intel2 | oth-ubuntu-1564122-1793621365 | scratch2/claude/codex-l4-drv-checkpoint-0138 | FINISHED exit0 | checkpoint saved, PG 184,252/0, clock PASS | FLOW-22 / DIE-S81-48 | |
| L4 fresh PA r1 / r2 | intel2 / intel1 | oth-ubuntu-323884-1793632998 / oth-ubuntu-3510479-1793634692 | scratch2/claude/codex-l4-fresh-pa-r2-0912/kit/FRESH_PA_RESULT.json | r1 FAILED (SWIG API), r2 FINISHED 09:33 | pin-access-only PASS, PG 184,252/0, 434 clock nets unchanged | FLOW-22 | does not explain FlexPA SIG11 |
| HF reserved-bit diagnostic | intel2 | oth-ubuntu-2954021-1793626613 | - | FINISHED exit0 | X-validity STEP PROVED (ddbf501cd) | TOK-HBM-1 | |
| TT23 old/fresh frontend pair | intel1 | oth-ubuntu-525152-1793639684 | scratch2/claude/codex-flow-tt23-frontends-PREP-1045/out/FRONTEND_ONLY_RESULT.json | FINISHED exit0 | frontend pair produced, no LEC credit | DIE-QC-63 | next: 23-way miter |
| Tnode retained-GRT DRT | intel2 | oth-ubuntu-319272-1793632983 | - | FINISHED exit0 | DRC0 at iter 6, ANT0, PG 31,224/0 | DIE-HBM-58 | |
| Tnode filler first target | intel2 | oth-ubuntu-1918998-1793638988 | scratch2/claude/codex-tnode-fill-prep-0910 | FAILED exit2 | FULL_POST_NOT_REACHED: wrong PRE/POST_FILLCELL hook names | DIE-HBM-58 (FLOW-22 hook) | R2 not run |
| VEs gate-frozen diag (+r1) | intel2 | oth-ubuntu-1946537-1793639087 + r1 | scratch2/claude/codex-ves-gate-frozen-0855-r1/kit/VES_FROZEN_CLOCK_DIAGNOSTIC.json | FINISHED | TT-4.15/FF+6.52 | DIE-S81-48 | SIGNOFF-SPRINT-21 already runs VEs eco_loop (18:05) |
| VEs qualified GRT-only repair | intel2 | oth-ubuntu-68398-1793631928 | scratch2/claude/codex-ves-h12-prep-0524/pass_m12_r1 | FINISHED exit0 | GRT checkpoint, PG 337,566/0, clock frozen PASS | DIE-S81-48 | |
| PSlice corrected PLACE | intel2 | oth-ubuntu-128328-1793632178 | scratch2/claude/codex-pslice-trunk-join-0425/kit/run_place.log | FINISHED exit0 08:04 | 3_place written; LOOK c79f3cf7f: PG 69,318 null terms, 3150 captures > 405 -> HOLD | DIE-HBM-58 | |
| RECIP make-n / PLACE canary / saved read | intel2 | 306392 / 413122 / 614166 | scratch2/claude/codex-recip-place-canary-prep-0810 | FINISHED exit0 x3 | PLACE +628 buffers, saved PG 106,210/0 (d43e0a057) | DIE-KV-61 | |
| AP reader build | intel2 | oth-ubuntu-533913-1793633772 | scratch2/claude/codex-ap-reader-0905/apreader.so | FINISHED exit0 | module SHA 425d9c25 | FLOW-22 | |
| Native filler mechanism | intel1 | oth-ubuntu-948983-1793624854 | scratch2/claude/codex-pg-birth-fill-0312 | FINISHED exit0 | 7 fillers, PG 18/0 | FLOW-22 | |
| QC PHY pair / FDI calendar / SAFE-LAND diags | intel2/intel2/intel1 | 4087940 / 1822435 / 1329617 | results/qc_phy_pair_1101 | FINISHED exit0 x3 | FDI edge101 missed; SAFE edge115 LOST (counterexamples) | DIE-QC-63 | feeds O24 |
| HBM OBS136 proof | intel1 | oth-ubuntu-1610218-1793627079 | scratch2/claude/codex-hbm-obs136-0450 | FINISHED exit0 | induction PASS (15e4f8d2f) | TOK-HBM-1 | |
| HG9 q1 SYNTH r1 / r2 | intel1 | 3232165 / 3267841 | scratch2/claude/codex-hg9-q1-synth-0750 | r1 FAILED (no synth), r2 FINISHED | 21,931 inst / 4 SRAM / 9785 seq | DIE-KV-61 | |
| HG9 q1 official LEC | intel1 | oth-ubuntu-3474197-1793634582 | scratch2/claude/codex-hg9-q1-lec-0820/proof/lec.json | FINISHED exit0 10:55 | EQUIVALENT 19,533/19,533, 0 differ, 11,147 s | DIE-KV-61 | Codex last said running: now PASS, collect |
| LLfd CTS PG canary | intel2 | - | scratch2/claude/codex-pg-birth-cts-0219/cts_pg0_0253 | NOT RUN | source review CONCUR 1f478d9d4 | DIE-S81-48 + FLOW-22 | = O26 |
| BFQG PG-only / Tnode fill R2 / L1 retained-route / Hroot 0830 | - | - | codex-bfqg-guide-pgfix-0200, codex-tnode-fill-prep-0910, codex-hroot-chunk-STRICT-PREP-0830 | NOT RUN (prepared) | - | DIE-HBM-58 / DIE-QC-63 / DIE-KV-61 | = O17/O27 |

### B. QC / HEAD (subagent, checked 18:1x-18:3x)
job_id | host | unit/container/controller | path (result dir/log) | state | result | owner_lane | note
--- | --- | --- | --- | --- | --- | --- | ---
QC frozen clock source-kit4 (ot_clk kit, DME) | intel1 | oth-ubuntu-856593-1793624595, workers pid 1080851/1080852 | /srv/opentallas-scratch2/claude/codex-qc62-clock-frozen-source-1102/emitted4 (+source_kit4.log, which is empty) | RUNNING-HUNG(13h05m, CPU still busy) | No result yet. check4 PASS. Two die_trial.py workers each at about 97% CPU with 12h40m CPU time. RSS 4.4/4.2 GB and creeping up (about +1 MB per 20 s). Newest file is emitted4/kit/abstracts/*.lef at 05:14. No source_kit4.rc, no clock files, no errors. | DIE-QC-63 | Not looping on I/O: compute-bound in DME with no output. Codex called it "live, preserve". COORD to decide whether to keep waiting.
KW place slw_st_a_v2__cl9f076a5c | epyc2 | oth-ubuntu-2605092-1793601009 / dpkit-slw_st_a_v2__cl9f076a5c-2625465 | /srv/opentallas-scratch2/claude/codex-qc-wave-1101/kit-wave/qwen_compute/5271d9d7…/items/slw_st_a_v2__cl9f076a5c/gen/…/run_place.log | RUNNING-LOOPING(19.6h) | GPL Nesterov at iteration 44910. Overflow has hovered 0.34–0.42 since iteration 5000 (0.40 now); target is about 0.1, so it never converges. Fixed instances about 195k, util 4.46%, target density 0.5. | KW-FIX-1 | The log moves but makes no progress. One failure class shared by every slw/sle_st place job below: about 50% fixed instances with util about 4–4.6% leaves GPL overflow stuck at 0.37–0.50.
KW place slw_st_a_v2__clf4365a62 | epyc2 | oth-ubuntu-2668568-1793601353 / dpkit-slw_st_a_v2__clf4365a62-2684993 | …/5271d9d7…/items/slw_st_a_v2__clf4365a62/…/run_place.log | RUNNING-LOOPING(19.5h) | GPL iteration 83660. Overflow 0.49–0.51 flat since iteration 10000. | KW-FIX-1 | Same class.
KW place slw_st_a_v1__clb036e152 | epyc2 | oth-ubuntu-2725425-1793601613 / dpkit-slw_st_a_v1__clb036e152-2747181 | …/items/slw_st_a_v1__clb036e152/…/run_place.log | RUNNING-LOOPING(19.4h) | GPL iteration 40800. Overflow 0.32 → 0.38, not falling. | KW-FIX-1 | Same class.
KW place slw_st_a_v1__clfc5867a6 | epyc2 | oth-ubuntu-754384-1793611492 / dpkit-slw_st_a_v1__clfc5867a6-754446 | …/items/slw_st_a_v1__clfc5867a6/…/run_place.log | RUNNING-LOOPING(16.8h) | GPL iteration 38380. Overflow 0.32 → 0.40, rising. | KW-FIX-1 | Same class.
KW place sle_st_a_v1__cl67389ecd (attempt_3) | intel2 | oth-ubuntu-1195910-1793608756 / dpkit-sle_st_a_v1__cl67389ecd-2902833 | /srv/opentallas-scratch2/claude/codex-qc-wave-1131/kit-wave/qwen_compute/d90b1092…/items/sle_st_a_v1__cl67389ecd/attempt_3/gen/…/run_place.log | RUNNING-LOOPING(16.2h) | GPL iteration 43710. Overflow about 0.49 flat since iteration 10000. Fixed 202800, util 4.63%. | KW-FIX-1 | Same class.
KW place sle_st_b_v2__cl14c98df5 | intel2 | oth-ubuntu-1729100-1793601642 / dpkit-sle_st_b_v2__cl14c98df5-2046897 | …/items/sle_st_b_v2__cl14c98df5/gen/…/run_place.log | RUNNING-LOOPING(19.3h) | GPL iteration 42380. Overflow 0.38 flat. | KW-FIX-1 | Same class.
KW place slw_st_b_v2 (attempt_3) | intel2 | oth-ubuntu-1824717-1793601926 / dpkit-slw_st_b_v2-1874607 | …/items/slw_st_b_v2/attempt_3/gen/…/run_place.log | RUNNING-LOOPING(17.0h) | GPL iteration 40470. Overflow 0.39–0.40 flat. | KW-FIX-1 | Same class.
KW place sle_st_a_v1__cl989804f6__cled3c1d7b (attempt_3) | intel2 | oth-ubuntu-1866958-1793602024 / dpkit-…cled3c1d7b-2511987 | …/attempt_3/gen/…/run_place.log | RUNNING-LOOPING(18.9h) | GPL iteration 30570. Overflow 0.44 flat. | KW-FIX-1 | Same class.
KW place sle_st_b_v1 | intel2 | oth-ubuntu-1890997-1793610891 / dpkit-sle_st_b_v1-3326877 | …/items/sle_st_b_v1/gen/…/run_place.log | RUNNING-LOOPING(15.8h) | GPL iteration 33670. Overflow 0.37 flat. | KW-FIX-1 | Same class.
KW place sle_st_b_v2__clfde1249e | intel2 | oth-ubuntu-2061954-1793602626 / dpkit-sle_st_b_v2__clfde1249e-2051022 | …/items/sle_st_b_v2__clfde1249e/gen/…/run_place.log | RUNNING-LOOPING(16.9h) | GPL iteration 39110. Overflow 0.37–0.39 flat. | KW-FIX-1 | Same class.
KW place sle_st_a_v2 (attempt_3) | intel2 | oth-ubuntu-2188293-1793602999 / dpkit-sle_st_a_v2-2079624 | …/items/sle_st_a_v2/attempt_3/gen/…/run_place.log | RUNNING-LOOPING(16.9h) | GPL iteration 30500. Overflow 0.44 flat. | KW-FIX-1 | Same class.
KW place sle_st_a_v1__cl989804f6__cl18eece69 (attempt_3) | intel2 | oth-ubuntu-43405-1793607129 / dpkit-…cl18eece69-2901171 | …/attempt_3/gen/…/run_place.log | RUNNING-LOOPING(16.2h) | GPL iteration 32180. Overflow 0.45 → 0.46, rising. | KW-FIX-1 | Same class.
(extra, not Codex's) KW place slw_hc2__cla3497502__cl16607c7a | epyc2 | oth-ubuntu-1901899-1793550737 / dpkit-slw_hc2__…-1964402 | /srv/opentallas-scratch2/claude/kit-wave/qwen_compute/5346b95c915/items/slw_hc2__cla3497502__cl16607c7a/gen/…/run_place.log | RUNNING-LOOPING(34h) | GPL iteration 87600. Overflow 0.36 flat. | KW-FIX-1 | Same failure class, from the older autopilot wave.
geom_check sle_fw_v1__cl9d029624 attempt_4 | intel2 | oth-ubuntu-1070367-1793608375 / ap-ageom-kw-sle-fw-v1--cl9d029624-grt-1112083 | geom dir …/codex-qc-wave-1131/…/items/sle_fw_v1__cl9d029624/attempt_4/geom (newest file grt.log 16:17) | RUNNING-slow(17.7h; last log line 2h ago) | GRT on 3_place.odb, M2–M7. "Found 0 clock nets": clk (32083 terminals) and 9 fclk nets (1–4k terminals each) are routed as signal. Now at extra iteration 19/50, about 55 min per iteration, so another 30 h or more. geom.tsv dumped at 00:36. | KW-FIX-1 | Brief listed this as codex-qc-event-1131. In practice hung. Root cause looks like clock nets routed as signal in the geom GRT.
geom_check sle_fw_v2__cl6740750e attempt_2 | intel2 | oth-ubuntu-1426550-1793620869 / ap-ageom-kw-sle-fw-v2--cl6740750e-grt-1426818 | …/items/sle_fw_v2__cl6740750e/attempt_2/geom (grt.log 17:25) | RUNNING-slow(14.4h) | GRT extra iteration 18/50. | KW-FIX-1 | Same as above.
geom_check sle_fw_v2__cl69f5e854 attempt_2 | intel2 | oth-ubuntu-2126004-1793611527 / ap-ageom-kw-sle-fw-v2--cl69f5e854-grt-2420689 | …/items/sle_fw_v2__cl69f5e854/attempt_2/geom (grt.log 17:08) | RUNNING-slow(16.6h) | GRT extra iteration 19/50. | KW-FIX-1 | Same as above.
geom_check slw_fw_v1__clf51c11d8__clc7ddab13 | intel2 | oth-ubuntu-1624527-1793601346 / ap-ageom-kw-slw-fw-v1--clf51c11d8--clc7ddab13-grt-1804017 | /srv/opentallas-scratch2/claude/codex-qc-wave-1101/…/items/slw_fw_v1__clf51c11d8__clc7ddab13/geom (grt.log 15:31) | RUNNING-HUNG-ish(19.4h; last line 2h45m ago) | GRT extra iteration 19/50. | KW-FIX-1 | codex-qc-glue worktree.
geom_check slw_fe_v2__clf110fab2 | intel2 | oth-ubuntu-2852744-1793605007 / ap-ageom-kw-slw-fe-v2--clf110fab2-grt-3785687 | …/codex-qc-wave-1101/…/items/slw_fe_v2__clf110fab2/geom (grt.log 17:06) | RUNNING-slow(18.4h) | GRT extra iteration 23/50. | KW-FIX-1 | codex-qc-glue worktree.
L1 2-LVT ordinary route2 | epyc2 | oth-ubuntu-3747083-1793607615 (svc codex-qc-l1-lvt-route2-1102 failed) | /srv/opentallas-scratch2/claude/codex-qc-l1-lvt-route2-0015/route.log | FAILED | Exit 2. DRT ended with 2 violations (M4 shorts against SRAM VDD). Then 5_3_fillcell DPL-0050 "No fillers found for LVTN". 5_2_route.odb retained. | DIE-QC-63 | Matches Codex.
L1 conditional signoff follower | local | codex-qc-l1-lvt-signoff-follow-1102.service (failed) | /srv/opentallas-scratch/claude/qc-l1-lvt-actual-1101/signoff_follow_status.json | FINISHED | HOLD_ROUTE_FAILED, route_exit 2. No STA was run. | DIE-QC-63 | —
L1 DRC audit | epyc2 | oth-ubuntu-1603071-1793617718 and 1631975-1793617837 | codex-qc-l1-drc-audit-1102 | FINISHED | Exit 0. The M4 obstruction is already present; 7-guide outside-SRAM proposal. | DIE-QC-63 | —
L1 same-input guard API | intel1 | oth-ubuntu-3203858-1793618752 | codex-qc-l1-retained-guard-api-1102 | FINISHED | Exit 0, PASS: 272919 instances / 280298 nets, 0 errors. | DIE-QC-63 | —
L1 guide-input native | intel1 | oth-ubuntu-2793564-1793631932 | codex-qc-l1-guide-input-1102 | FINISHED | Exit 0, PASS: 7 guides round-trip, only the target wire ripped, all else unchanged. | DIE-QC-63 | The retained-route repair (4d31e85cd) was never launched; it needs scope.
L7 final guide rewrite | intel1 | oth-ubuntu-2028860-1793614808 | codex-qc-l7-finalguide-1102 | FINISHED | Exit 0. 1926 CLOCK / 276894 SIGNAL nets, 0 missing. | DIE-QC-63 | The original L7 GRT container outer rc1 (stale guide) is preserved.
L7 GRT readout (p-qc) | epyc2 | oth-ubuntu-1386798-1793615800 | /srv/opentallas-scratch2/claude/codex-qc-l7-readout-1102/final_grt_timing_readout.json | FINISHED | rc 0. TT setup −3.56 / hold +9.09 (pinreg 405.03). FF hold +0.46 / setup +227.08. Both bands PASS. | DIE-QC-63 | Global-route RC estimate only.
L7 six-negative / 4-LVT PREP | intel1 | oth-ubuntu-3639274-1793620282 | codex/g0c-regress-1101 d8e5893e1 | FINISHED | Exit 0, TT −3.560152 / TNS −7.72. | DIE-QC-63 | —
L7 four-LVT native trial | intel1 | oth-ubuntu-1086720-1793625281 | results/qc_l7_lvt_1102/actual_trial (a25f4f2dd) | FINISHED | Exit 0. TT +0.19 / hold +9.09. FF hold +0.46 / setup +227.08. PG 545100/0. | DIE-QC-63 | —
L7 full geometry | intel1 | oth-ubuntu-2920748-1793632382 | codex-qc-l7-full-geom-1102 | FINISHED | Exit 0. Pin 10.02/57.94, r2r 336.2/0, leaf 48.98. Raw partial_face1 / density WARN retained. | DIE-QC-63 | The ordinary-DRT capsule (d009d1795) is disabled pending an OWNER question.
SC 3-BUF geometry | epyc2 | oth-ubuntu-1067116-1793613522 | codex-qc-sc-red-1101/sc_buffer_geometry | FINISHED | Exit 0. Max pin hop 112.5, PG 751910/0. | DIE-QC-63 | —
SC 3-BUF replay | epyc2 | oth-ubuntu-1138584-1793613938 (frontend intel2 PID 2897509) | …/sc_buffer_replay/postcts_gate_{tt,ff}.json | FINISHED (exit 1 from observer) | Full GRT overflow 0, 370320 nets. TT setup −388.81 / hold −166.2. FF hold −163.48 / setup −221.23. FAIL. | DIE-QC-63 | Exit 1 came from the missing clk_freeze observer after the ODB was saved. Codex did not report the FF setup −221.23 figure.
SC replay path diagnosis | epyc2 | oth-ubuntu-1230831-1793614575 | …/sc_buffer_replay/sc_{TT,FF}_paths.rpt | FINISHED | Exit 0. Worst path is now dn44 u_15645. | DIE-QC-63 | The SC dn44 2-BUF, SC49 and nominal-role (384ec7774) jobs are all NOT-RUN.
RED native GRT | epyc2 | oth-ubuntu-3094774-1793603597 | …/codex-qc-sc-red-1101/red_grt/grt_only.log | FAILED | Exit 2. CLK_GEOM_DIFF: 1 instance changed (u.u_143133/Q$_DFF_P_ resized). 8270 clock nets unchanged. No post-repair ODB. | DIE-QC-63 | red_grt_ffpreserve and _pg1 are prepared but NOT-RUN.
Prefix access origin2 | epyc2 | oth-ubuntu-4055723-1793609838 | codex-qc-nl-prefix-1101/prefix_access_origin2 | FINISHED | Exit 0, PASS: 51596 cells, 0 access collisions. PG 103192 unbound (pending). | DIE-QC-63 | —
NL final50 GRT | intel1 | oth-ubuntu-3960903-1793595959 | codex-qc-nl-prefix-1101/nl | FINISHED | Exit 0, PASS. GRT overflow 0, M2–M7. 1184 CLOCK + 68340 SIGNAL nets. | DIE-QC-63 | READY ae91422ab.
CORE source graph v2 | epyc2 | oth-ubuntu-1244685-1793614700 | codex-qc-core-sourcegraph-1102/v2 | FINISHED | Exit 0. 215597 std / 63971 FF / 0 undriven / 0 cycles. | DIE-QC-63 | —
CORE reset NIO attempt2 | intel1 | oth-ubuntu-3160957-1793633347 | codex-qc-core-reset-nio-a5-1102 (dispatch2.log) | FINISHED | Exit 0. Result not read. | DIE-QC-63 | Codex last reported it as "active". Many codex-qc-core-nio-* dirs were created afterwards, with no live units.
TT_C fast home solver | epyc2 | oth-ubuntu-1049885-1793613433 | codex-tt-locality-1102 | FINISHED | Exit 0 (v2 03b17ac85: 45301 constraints, max 405). | DIE-QC-63 | —
TT_C row87 joint solve | intel1 | oth-ubuntu-550012-1793623734 | codex-tt-locality-1102/rowprep_v3/terminal_oom_journal.log | FAILED | Exit 137, OOM-kill at 08:49 (4 GB cap, 4h54m). | DIE-QC-63 | Codex called it "healthy" at 08:24; it died after. Source-only successors rowprep_v4/v5 (diagnosis JSON, 09:04–09:19) exist with no job running.
TT_C source SYNTH | intel1 | oth-ubuntu-2659396-1793631363 | codex-tt-locality-1102/synth_join_prep | FINISHED | Exit 0, PASS. | DIE-QC-63 | —
TT_C native join | intel1 | oth-ubuntu-2949741-1793632499 | — | FAILED | Exit 1, FAIL_CLOSED. 23 anonymous names drift; 244 masters differ. | DIE-QC-63 | Intentional fail-closed.
TT_C comparator SAT | intel1 | oth-ubuntu-3390831-1793634231 | — | FINISHED | Exit 0. 133-leaf D function PASS; mutant rejected. | DIE-QC-63 | —
TT_C clock-aware runs | intel1 | oth-ubuntu-3772880-1793620752 and 3799214-1793620835 | — | FINISHED | Exit 0. | DIE-QC-63 | —
HEAD native lemma R4 | epyc2 | oth-ubuntu-1420301-1793616099 | codex-head-native-lemma-r4-1102 | FINISHED | Exit 0, PASS. 12 KEEP/hunt joint STEP + BASE64. The 16 ld still STEP DIFFER. | FLOW-22 | —
HEAD typed70 native | epyc2 | (unit not recorded) | /srv/opentallas-scratch2/claude/codex-head-typed70-0248/TYPED70_RESULT.json | FINISHED | TYPED70_BOUNDED_DIAGNOSTIC_PASS. Matched 58437, prior 12732, conflicts 0. No change to the default gate. | FLOW-22 | —
HEAD 469-point native | intel2 | oth-ubuntu-473228-1793633560 | — | FINISHED | Exit 0. 172 UNPROVEN → PROVED. 297 still DIFFER. | FLOW-22 | No full sender credit.
HEAD HOST clock audit | epyc2 | oth-ubuntu-1310838-1793615222 | codex-head-host-clock-audit-1102/audit.json | FINISHED | Exit 0. Two BUFx24 A=NULL in 6_final (real disconnect, arising inside CTS). | DIE-HEAD-54 | —
HEAD SPN band fix placement | epyc2 | oth-ubuntu-1334981-1793615410 | codex-head-spn-bandfix-1102/geom | FINISHED (exit 1) | Native placement PASS. Outer raw-geom hold: pin max 139.83, r2r 390.28, tap 1993 > 1500. | DIE-HEAD-54 | —
HEAD SPN_END B_p2 audit | intel1 | oth-ubuntu-2913523-1793632359 | /srv/opentallas-scratch/claude/head-spnend-clock-audit-1102/ACTUAL_FINAL.json | FINISHED | Exit 0. 4 exports A_NULL. Signoff NOT SIGNED: TT +62.58 / FF −3.54, DRV 108/37, DRC 3, LEC UNPROVEN 4. | DIE-HEAD-54 | —
HEAD SPN_END D post-route DRV | intel2 | pid 1967141 prd_run.sh / container prd-prd53-hd_spn_end_D-1967141 (watcher codex-head-spnend-D-watch-1102.service is live) | /srv/opentallas-scratch2/claude/die-head-48/prd53/hd_spn_end_D/run_prd.log | RUNNING-HUNG(4h30m; up 32h50m) | DRT 30th iteration finished with 53 violations (3h47m). The 31st iteration printed "10%" at 13:56 and nothing since. 100% CPU, 26.3/32 GB. | DIE-HEAD-54 | A legacy DIE-HEAD-48 job. The watcher only collects results; it does not launch anything.
HEAD n4 ECO pilot | intel2 | kw-eco-1 eco_loop (exec 796908) | /srv/opentallas-scratch2/claude/kw-eco-1/pilot/hd_st_n4/eco_20261101_215110_796908/eco_loop.json | FINISHED | EXHAUSTED 15:54. Best is i2: TT +141.57 / FF +7.84 / DRV 33 (12 TT / 21 FF) / DRC 0, NOT SIGNED. i3 gave no improvement. | DIE-HEAD-54 | Retained D_p2 (TT 146.30 / FF 7.58) is still the comparison point. The n4 collect watcher is gone.
HEAD Turn paired profile | intel1 | oth-ubuntu-1945396-1793628422 | — | FINISHED | Exit 0. TT −340.16 → −202.66, FF hold +10.01. | DIE-HEAD-54 | Diagnostic only.
HEAD wave path query | intel1 | oth-ubuntu-1428080-1793626422 (svc codex-head-wave-path-query-1102 failed) | /srv/opentallas-scratch2/claude/codex-head-wave-path-query-1102 | FAILED | Exit 1 at 05:38. resume_missing.sh then produced hd_spn_eshim_tx and hd_st_n3_turn dirs (05:43–05:45). | DIE-HEAD-54 | Result content not read.
HEAD 94510 wave units (mesh_e, n3_turn, eshim_tx, n3_transit) | intel2 | kw-s81hea-*-94510.service | /home/ubuntu/coord/autopilot/kit_wave/s81_head_*/a1/ | FINISHED | No longer active. Codex: three are PASS-COND (geom PASS-COND / AP_RC 0); old mesh raw geom FAIL. | KW-FIX-1 | Still needs normal collect() + enqueue_pass under kit_wave.lock. The ledger still shows RUNNING.
QC proposal9 / base bind, UCIe/CORE counts, SC PLACE r3, SC timing / path, L1 LVT GRT / review / import, prefix preflight | epyc2/intel2 | 2909983, 3109339, 3665302, 778163, 867333, 3423450, 3555886, 2771528, 4046883 | various codex-qc-* | FINISHED | All exit 0, matching the checkpoint numbers. | DIE-QC-63 | Historical (before 02:00) but still inside the window.
QC current-clock join (1364730) | intel2 | oth-ubuntu-1364730-1793567323 | codex-qc62-collect-1101/clock_source_current_d90_join.json | FINISHED | SUCCESS. Cohort mismatch: 324 missing, 1816 XY differences, 104 driver differences. | DIE-QC-63 | —
SC49 / SC dn44 / RED ffpreserve(_pg1) / L1 retained repair / L7 DRT | — | — | prepared capsules | NOT-RUN | Prepared and disabled; each waits for scope. | DIE-QC-63 | —

READY items
- codex/qc62-collect-1101@82190c1ff: frozen canonical-base strict bind PASS.
- codex/qc62-ucie-held-1101@4b5c115dd: HELD UCIe/CORE prep. Later CORE held tips are 149c74f82 → 70e8bec37 (candidate3).
- codex/g0c-regress-1101@0392073bc, 8fa1f8202, 3c8e2de8f: L1 BUF/LVT receipts. Then:
  - 2627782dc: L1 route failure packet.
  - 203b1c9d7: L1 guide PREP.
  - 2c130cd71 and 4d31e85cd: L1 retained-repair capsule.
  - f02efdb89: L1 guide-input PASS.
  - d8e5893e1: L7 4-LVT PREP.
  - a25f4f2dd: L7 4-LVT trial PASS.
  - cefe8648a / a0a810d58: L7 geom LOOK reviews.
  - d009d1795: L7 DRT capsule (disabled).
- codex/qc-sc-red-results-1101@c622e3c5a: SC/RED results only. Later tips: 2461a8a06 → ab0dce14d → 6d47416b9 (SC49 + RED PG option) → 384ec7774 (nominal-role adapter) → 4066dba2b (SC49 route/readout PREP).
- codex/qc-neighbor-counts-1101@c2b571529: neighbor COUNT/ABI/FACE PASS.
- codex/qc-prefix-access-1102@eff1f5cf1 then ec0e8eb70: prefix access FAIL plus corrected PASS.
- codex/qc-nl-final50-1102@ae91422ab: NL final50 GRT PASS.
- codex/head-collect-1101@8f80ad467 then 9b4b5fe32: mesh join and sender diagnosis.
- codex/head-ld-source-1102@47bcebc6d, 886ef7c00, 0a99f6ca7: 16-ld / 70-field source trace.
- codex/tt-locality-prep-1102:
  - f60cfd6d2 → 0d16c7af3 → bb03aa5f3 → bed068146: TT_C source/model.
  - 03b17ac85: clock-aware v2.
  - a7ebca003: native join PREP.
  - 7138f11f0: fresh-source census.
  - c570fe8ee: source state.
- codex/eco-postroute-lec-1102@76144c718: HEAD 12/12 lemma results.
- codex/qc-phy-pair-2345@bd08c4063: private two-peer PHY boundary test.
- codex/qc-serdes-clocktrace-0010@3c1869bd8: SerDes clock domain trace.
- codex/head-wave-collect-1102@3660cbbde → 07c5f4904 → 48d62f5bb → dff2d2c43: HEAD wave collection (TileIO/SPN/TileA/Transit/Turn). Related commits:
  - 587c36275: forward-clock continuity guard.
  - 323ab8c0b: F-variant collection.
  - b53c286f2: disabled restore API.
  - 43e49c51f: source consumer proposal.
  - faf669a42: SerDes lineage export.
  - 69812606f: padding-preserve alternative.
- fa72afc8b: QC frozen clock source capsule.
- a90f78f50 / 078d029ad: typed70 independent reviews.
- codex/pg-filler-1102@d9b35c122: strict native filler mechanism PASS.
- ffd77aa7e: SAFE1 pulse-loss proof.
- 594c0dca0: retained-event FDI alternative (default OFF).
- 1962a25ca: GEOM packet (BFQG, L1 guide, L7 PREP, HFDEP).

### C. S81 / DS (subagent)
Codex left about 40 S81/DS jobs. All are accounted for below except two: the T51 GEOM waiter, and the T41 PLACE row that the ledger still shows as RUNNING (rows 37–38). Five units are still live, and one of them, the KV-bridge synth, has been silent for 14.7 h. The Codex prose disagrees with the result files in a few places: the BF hold ECO failed GRT, both EG LECs are NOT EQUIVALENT, and the VEs hold12 run reached only +2.64 ps hold. None of these were collected in the handoff.

job_id | host | unit/container/controller | path (result dir/log) | state | result | owner_lane | note
---|---|---|---|---|---|---|---
VS8 eight-net DRT (codex-s81-vs8-1131) | intel2 | oth-ubuntu-664216-1793566115 / container angry_roentgen (8 CPU, 14.2 GB of 24 GB) | /srv/opentallas-scratch2/claude/codex-s81-vs8-1131/eight_route.log | RUNNING, log last written 17:23 (45 min old), but not converging | 3 M3 shorts left; stubborn-tile iteration 53 is at 50% after 5 h 52 m; down from Codex's 28 at 02:00 | DIE-S81-48 | Started 11-01 21:52, 20 h running. COORD should decide whether to keep it; I did not stop it.
DS V1c3 serial make (codex-ds-v1c3-serial-0128) | epyc2 | oth-ubuntu-783691-1793611608; intel2 client pid 2156339 | /srv/opentallas-scratch2/claude/codex-ds-v1c3-serial-0128/resume_make.log | RUNNING, progressing (log 18:13) | 405 compile lines so far; 0 errors or kills; started 01:30, 16 h 45 m CPU | TOK-DS-3 | Memory peak reached the 64 GB cap (now 32 GB) with no OOM yet. Watch for OOM.
DS IMG2 serial make (codex-ds-img2-serial-0120) | intel1 | oth-ubuntu-545428-1793610022; intel2 client pid 1602009 | /srv/opentallas-scratch2/claude/codex-ds-img2-serial-0120/resume_make.log | RUNNING, progressing (log 18:10) | Queued until 14:02, then started; 58 compile lines; 0 errors; peak 38 GB of 64 GB | TOK-DS-3 | Uses the same 133 GB cache.
S81 KV-bridge whole-KV SYNTH (codex-s81-kvbridge-size-2111) | intel2 | oth-ubuntu-1159241-1793599785 / container codex-kvbridge-size-2111-1181066; local ot-run client pid 531391 | intel2 …/codex-s81-kvbridge-size-2111/run/logs/asap7/kvbridge_size_2111/base/1_2_yosys.log; local otrun.log | RUNNING-HUNG (14.7 h with no log output) | Yosys has sat in the SHARE (SAT resource sharing) pass since 03:28; 100% CPU, 24.1 GB of 32 GB, 19 h CPU; no mapped count yet | DIE-S81-48 (geometry peer) | This is the same job the handoff calls "sole wholeKV SYNTH unit1159241". It is not a separate job. Likely stuck in SAT sharing; COORD decides.
resign-vsw_q_s81-lec | epyc2 | container resign-vsw_q_s81-lec | none found | UNKNOWN | The container is gone from `docker ps -a`, and no matching directory exists in scratch | SIGNOFF-SPRINT-21 | Probably a Claude lane; noted only.
BF controlled FFhold12 ECO (codex-s81-bfA-2258) | intel2 | oth-ubuntu-2105547-1793602756 | /srv/opentallas-scratch2/claude/codex-s81-bfA-2258/eco/i1/run_prd.log, eco_loop.json | FAILED (exit 1, 08:54) | Route rc 2: GRT-0232 congestion too high (M3 1529 / M5 755 congestion, total 2444) after 8 h 52 m. Base TT −0.84 / FF −24.25 / DRV 16, so the late-ECO loop gave up after 1 iteration | DIE-S81-48 | Not collected by Codex. The other BF run, container 2f00c01631b5 (peco-dsfd_bf_front_roots_ck12B-E-a), is still up 2 days at 301% CPU.
EG ccA 24 GB LEC | intel1 (kit on intel2) | container 1618070ed22c (gone) | /srv/opentallas-scratch2/claude/codex-s81-cohort-1101/kits/ot_s81sl_eg_ccA/lec_retry1131/lec.json | FINISHED (09:40Z) | FAIL: NOT EQUIVALENT, 40184 of 40190 points proved, 6 differ (first: u_nh.rsqrt.g_nr[*].m_hm.g_l5.u.u.y[31]), 0 undecided | DIE-S81-48 | Both A and B fail on the same rsqrt points. New klegacy-resume-kit_ccA/ccB containers started on intel2 at ~18:05, probably a Claude lane.
EG ccB 24 GB LEC | intel1 | container 95f259e203a3 (gone) | …/ot_s81sl_eg_ccB/lec_retry1131/lec.json | FINISHED | FAIL: NOT EQUIVALENT, 40184 of 40190, 6 differ (rsqrt y[31]) | DIE-S81-48 | See the ccA row.
VEs original AP a3 | intel1 | oth-ubuntu-1032642-1793611631 | /srv/opentallas-scratch2/claude/codex-s81-ves-2042/kit; receipt coord/tmp/codex-ves-auto-invalid-0508/receipt.json | FAILED (exit 1, 05:11) | Codex retired it by hand (route rc 137). Baseline was NOT SIGNED: TT +41.71, FF −9.29 | DIE-S81-48 | Retirement was deliberate, not an OOM.
VEs GRT-only successor | intel2 | oth-ubuntu-4116935-1793631377 | codex-ves-h12-prep-0524/pass_m12 | FAILED (exit 2) | Absolute ODB path bug; died before the DB loaded | DIE-S81-48 | Replaced by the r1 run below.
VEs hold12 GRT-only r1 | intel2 | oth-ubuntu-68398-1793631928 | /srv/opentallas-scratch2/claude/codex-ves-h12-prep-0524/pass_m12_r1 | FINISHED (rc 0, 08:06) | GRT checkpoint only. FF hold ws +2.64 ps (aimed for +12, below the +10 gate); SS setup +27.78; 2 hold buffers added; PG audit PASS 337566 terms / 0 failures; clock/reset freeze and source wire diff both 0 changes | DIE-S81-48 | Status says DRT_FILL_FINISH_HELD. Hold did not reach +10.
QBS LLfu gen10 full-PG GRT | intel2 | oth-ubuntu-1569011-1793621382 | /srv/opentallas-scratch2/claude/codex-s81-qbs-centre-2255 | FINISHED (rc 0) | PASS TT +11.73 / FF +10.00; PG0 | DIE-S81-48 | —
QBS NNfu gen11_allpg_sdc GRT + gate | intel2 | unit not recorded | …/codex-s81-qbs-centre-2255/gen11_allpg_sdc/dsfd_node_NNfu_c | FINISHED | PASS TT setup est +6.89 (band PASS); FF +8.51 per Codex | DIE-S81-48 | gen10 NNfu failed earlier (missing SDC) and was kept as history.
QBS LLfu gen12 DRT-only observational run | intel2 | none | …/codex-s81-qbs-centre-2255/gen12_drt_only/dsfd_node_LLfu_c/run_drt_observational.sh | NOT-RUN | Packet ready (06:03), no logs | DIE-S81-48 | Waiting on ROOT run admission (OWNER?).
QBS LLfd CTS callback canary | intel2 | none | /srv/opentallas-scratch2/claude/codex-pg-birth-cts-0219/cts_pg0_0253 | NOT-RUN | Runner staged at 07:53; nothing written since | DIE-S81-48 (with FLOW-22 for PG birth) | OWNER? at 07:51 asks to authorize one 8 GB/2T canary.
SOURCE39 BIND final_clockset_r2 | intel2 | oth-ubuntu-3259882-1793614902 | /srv/opentallas-scratch2/claude/codex-flow-s81-source-2055/bind.final_clockset_r2.client.log | FAILED (exit 1) | errors 1: slice_station__t49 clk_t25 radius 150.963 > 150 | FLOW-22 | Superseded by t49.
SOURCE39 BIND final_clockset_t49 | intel2 | oth-ubuntu-1252503-1793620193 | …/bind_final_clockset_t49/ | FINISHED (rc 0, 04:31) | PASS: 398 parts / 204 types / 873 crossings / 606281 bits; 0 errors, unbound, tied, undriven or multiply bound | FLOW-22 | Source-only; not activated.
SOURCE39 metadata capsule 0800 | intel2 | oth-ubuntu-167016-1793632342, then oth-ubuntu-265089-1793632753 | …/codex-flow-s81-source-2055/capsule_0800*.client.log | FINISHED | First unit exit 2, finishing unit exit 0. This is capsule 8b93c6acc; physical/source qualified = false | FLOW-22 | The latency_reviewable unit 4063849 also exited 0.
cl911 model r3 + lockstep | intel2 | oth-ubuntu-3040024-1793614307 / oth-ubuntu-3057810-1793614352 | /srv/opentallas-scratch2/claude/codex-s81-cl911-t28-0212 | FINISHED (rc 0) | PASS: tap28 load 404, radius 198.411; 212608 checks over 4895 cycles; mutant gave 2312 mismatches | DIE-S81-48 | READY af3619f17.
Canonical reset replan proof | intel2 | oth-ubuntu-3423102-1793615359 | results/geom_review/s81_canonical_reset_replan_0220 | FINISHED (rc 0) | PASS: 217440 checks, 2312 mutant mismatches; 186 relays | DIE-S81-48 | —
Hist COMB-only PLACE (familyck) | epyc2 | oth-ubuntu-906965-1793612422 | /srv/opentallas-scratch2/claude/codex-hist-combplace-familyck-0144/kit | FINISHED (rc 0, 02:43) | Guards PASS (31847 FF, 36809 TAP, 32 macros); max reach 404.946 < 405. Congestion HOLD: M2–M5 column peak 1.510 / channel 1.739 | DIE-S81-48 | No CTS or GRT. The PG-only saved copy is done in intel2 codex-pg-birth-hist-0300 (guard_saved.json 02:59).
Hist R3 clock source model | intel2/epyc2 | one-shot | codex-hist-clock-model-r3-complete-0442 | FINISHED | FAIL (structural model) | DIE-S81-48 | No further variants planned.
L4 after-DRV checkpoint | intel2 | oth-ubuntu-1564122-1793621365 | /srv/opentallas-scratch2/claude/codex-l4-drv-checkpoint-0138/run.log | FINISHED (rc 0, 05:31) | PASS checkpoint: 434 clock nets / 12902 instances unchanged; PG 184252 terms; 6 slew violations targeted; PG callback created 3 cells | FLOW-22 | Stopped before setup/hold/DRT as planned.
L4 fresh pin-access GRT | intel2 | oth-ubuntu-323884-1793632998 | /srv/opentallas-scratch2/claude/codex-l4-fresh-pa-0810/client.log | FAILED (exit 2) | global_route.tcl:5 "invalid command name _…dbAccessPoint_p…": a SWIG tool bug after 48 s | FLOW-22 | Same tool class as the earlier SIG11 FlexPA crash. Do not retry blind.
Cap WEST2 six-net GRT diagnostic | intel2 | oth-ubuntu-782944-1793634782 | /srv/opentallas-scratch2/claude/codex-cap-gate-0810/kit | FINISHED (rc 0); the readout query exited 1 | TT setup est −11.47 (FAIL); FF hold +10.00; clock band PASS | DIE-S81-48 | —
Cap D3 query r1 | intel2 | unit not recorded | /srv/opentallas-scratch2/claude/codex-cap-d3-query-0845-r1/kit/CAP_D3_DIAGNOSTIC.json | FINISHED | Diagnostic complete; the only required failure is setup_tt (FF clean) | DIE-S81-48 | Not signed.
Cap TT query / FF-only query | intel2 | oth-ubuntu-3237246-1793614854 / oth-ubuntu-3313423-1793615054 | coord/tmp/codex-caprt-0148 | TT FAILED (exit 1) / FF FINISHED (rc 0) | TT: timing done, then a metadata format error. FF: static loads written | DIE-S81-48 | Kept as is.
T7 canary2 | intel1 | oth-ubuntu-80731-1793597049 | …/codex-flow-s81-source-2055/t7.canary2.client.log | FAILED (exit 1) | memory_bits FAIL ×9; syntax/RTL/pin/clock all PASS | FLOW-22 | —
T7 PMEM staging proof | intel2 | oth-ubuntu-10967-1793631711 | /srv/opentallas-scratch2/claude/codex-s81-t7-stage-miter-0705/actual.log | FINISHED (rc 0) | PASS D32_NL4_TROWS640: 2544000 checks over 2400 cycles; wrong-address mutant caught 2400 | DIE-S81-48 | The follow-up "one minimum PMEM candidate" was authorized but I found no unit.
T51 data-comb / FT models (several one-shot dirs: t51-data-cone, regions, joint-spread, ft3-ownership, ft6-contact, domain-bridge, clocktap-feas) | intel2/intel1 | one-shot | /srv/opentallas-scratch2/claude/codex-t51-* (last 08:45) | FINISHED | Geometry model projects FAIL: M7 cut 2.24, column_v 2.703. ft6 one-contact witness PASS for one point; overall HOLD | DIE-S81-48 | No CAD.
DS R8-age native test | intel2 | oth-ubuntu-1132881-1793613902 | coord DS packet 5c86a737d | FINISHED (rc 0) | Uniform-41 PASS; as-built 46/45 delays FAIL (CFIFO fault 1); controls caught | TOK-DS-3 | —
DS BF phase106 / legacy XS gate / source bridge (codex-ds-bf-native-pair-0605, ds-legacy-xs-gate-0538, ds-bf-source-bridge-0442, ds-archive-reuse-0402, ds-reuse-pairs-0426) | intel2/epyc2/intel1 | one-shot | /srv/opentallas-scratch2/claude/codex-ds-* | FINISHED | BF phase106 (b70e77239) scoped PASS with all faults 0. XS gate PASS; its RC1 was only a harness label | TOK-DS-3 | No full build.
VSW current051 fresh LEC + ETM export | intel2 | oth-ubuntu-4015058-1793609674 / oth-ubuntu-809577-1793611765 | branch codex/vsw-publish-0130 | FINISHED (rc 0) | LEC PASS 15804/15804; SIGNED TT +54.47 / FF +10.18 | SIGNOFF-SPRINT-21 | Held for S81 release; no eligible PROVENANCE.json, so no count.
Hist rb2 diagnostic LEC | intel1 | oth-ubuntu-2802600-1793603944 | — | FINISHED (rc 0) | EQ 88093/88093 | DIE-S81-48 | Diagnostic only.
QBS9 parent glue LEC | — | oth-ubuntu-3065868-1793604678 | — | FINISHED (rc 0) | EQ 40321/40321 | DIE-S81-48 | Not counted as closure of the 9 bodies.
Hist anchored FP / anchor | — | oth-ubuntu-3335549-1793605546 / oth-ubuntu-3849835-1793607283 | codex/hist-bounds-2145 | 3335549 exit 1; 3849835 rc 0 | Anchor PASS; the first anchor had 1385 TAP overlaps | DIE-S81-48 | Superseded by the COMB-PLACE row.
QBS CTS PG repair / saved reread | epyc2 | oth-ubuntu-660072-1793610894 / oth-ubuntu-681858-1793611033 | coord/tmp/codex-qbs-cts-pg-0117 | FINISHED (rc 0) | PASS: LLfu 180 cells / 360 PG, NNfu 176 / 352 | DIE-S81-48 | —
SerDes locksafe 8 GB gate | intel1 | oth-ubuntu-3796322-1793595486 | coord/tmp/codex-serdes-locksafe-2047 | FINISHED (rc 0) | PASS 1011 checks | DIE-S81-48 / DIE-HEAD-54 | Source-only.
V1c3 original 96 GiB build | epyc2 | oth-ubuntu-182056-1793588951 | — | FAILED (exit 143) | OOM at the memory cap after 377 archives | TOK-DS-3 | Handled by the serial V1c3 continuation.
S81 wave T51 GEOM / T41 PLACE / t31 | intel1 | kit-wave b1a2125433d0 | ~/coord/autopilot/kit_wave_stages.tsv | UNKNOWN | Ledger: T51 geom FAIL, T41 place RUNNING (Codex says terminal GEOM FAIL), t31 RUNNING at 18:23 | KW-FIX-1 | The ledger and Codex prose disagree on T41. The serdes units are in the wave lane's file.

The table has 40 rows. Lane note: the brief names no QBS lane, so I gave QBS to DIE-S81-48. "ot-run localhost" here means intel2 (tolerant-swine).

READY items
- codex/s81-die-2032@c9021ed99: t18 clk_t16 tap move (follows 45744367f)
- codex/s81-die-2032@af3619f17 (+ helper input 3a0edb597): cl911 t28 repair; includes c902 t18
- codex/s81-die-2032@5674de5c0 (includes ecc65f214): canonical reset PREP, 186 relays
- codex/s81-die-2032@4290c9c99: SOURCE39 event review branch
- b00113f86: inactive SOURCE39 event prep (+6 control FFs, 0 cycles)
- 8b93c6acc: SOURCE39 clean metadata-overlay capsule
- 6604994a6: fresh-Plan t18/cl911 reset proofs (supersedes cached Plan)
- 60f4b5128: t49 tap repair
- 8b3648b7d: QBS full-block PG record
- 30428e20f: QBS centre-M5 generator/review
- 178a634c7: LLfd CTS-open membership rebalance helper
- 8322bb073 / 5621983f5: PG native callback adapter / native helper
- codex/hist-bounds-2145@6ea576e54, later e0bb0ba25: hist anchored FP / scalar-ck correction
- c778722d2, 973a98b46, 644c88312: hist COMB-PLACE, models, column recipe
- 1f736a0ae, 5fdd45fb8: hist rb2 receipts
- codex/vsw-publish-0130@fbc0b5c45 (includes 06f1619c9): VSW actual views; release held
- codex/serdes-locksafe-2047@ba934c4af (wrappers f52866809): SerDes LOCKSAFE reset candidate
- b83a6f2db: Cap image and diagnosis
- 38201bf87: XRT disabled contract proposal
- 4ef2 / 02b (short SHAs only): T7 metadata and census
- codex/ds-native-go-pair-2355@a38642c4e: 12 literal-bound joins
- codex/ds-native-go-pair-2355@5c86a737d (after b23c63e47): R8-age logs and package
- eabf0012e: DS cadence P142
- 77eadd758: DS selected mixed Q/BF PASS
- e58e7aa61 / 29db85fd5 / fd6835bb2: GO oracle correction and positives
- b70e77239: DS real BF phase106 PASS
- 8fb320689 / e5c51f96d / 5ea6e54d9 / 724d5332a / af4250865 / 6430864fb / 8d0009768: DS source-event prep
- 78be94479 / 7d59ad8f2: DS producer join
- 34217ce6f / 0d94aa8c6: DS source PREP with BF operand
- 0bb / 7bd (short SHAs only): DS inactive event and SID6 image candidate
- 140e7c54c: IMG2 launcher/receipt
- 6797dbbb1: whole-KV census

### D. KV / Qwen token (subagent). Update 18:44: the kvpeer x3 units are already inactive (exit 137, ended by another lane about 18:38); qkd_hr_core_prompt EQ was stopped as W3
No Codex KV/Qwen job was lost. Four units are still active, but one of them only has a sidecar LEC alive because its PLACE failed. Three docker EQ containers look hung. Eight jobs finished after the 08:24 stop and none of them has been collected yet: AHUB maxwire80, HG9 q1 proof, PC dataGRT, the PHY NRA results so far, three TT_C rowprep runs, and the old nwB sim.

job_id | host | unit/container/controller | path (result dir/log) | state | result | owner_lane | note
---|---|---|---|---|---|---|---
KV hostcredit corrected ready-wait/36-layer/d2d run_full | intel1 | oth-ubuntu-3950525-1793636503; local controller bash 1408053 (launch_restore32_chain.sh) → ot-run 2053931 | /srv/opentallas-scratch2/claude/codex-kv-hostcredit-top-2100/runs/full_readywait/{sim.log,observation_window.json} | RUNNING-progressing | boot PASS: frames 7404/7404, images 14/14, setup cyc 38493, faults 0. Last heartbeat cyc 100000 at 16:56. observation_window.json says AWAIT_DATES (post 290867, host_job OPEN_ROOT0_ABSENT). Speed ~3.3 cyc/s, so about 16 h more | TOK-QW-3 | die_to_host still 4 words and credits 4 at cyc 100k, the same symptom as the old consumer bug. Check this once the observation window opens. A separate TOK-QW-3 NOWAIT sim (unit oth-ubuntu-2990777-1793672394, started ~12:00) uses the same ELF; it is not Codex
KV production make (orig 32GB/j1 restore) | intel1 | oth-ubuntu-3386934-1793619373; controller codex-kv-credit-veh60-restore32-0355 | codex-kv-hostcredit-top-2100/continue_make.log | FINISHED | PASS exit 0 at 08:28. ELF 837825160 B, sha b0e76c8d…; 51 libs / 4765 CPP | TOK-QW-3 | Earlier 32GB unit 2762200 ended exit 143 (stopped for the 96GB attempt). The 96GB successor never ran
KV peer EQ alias2 | intel1 | oth-ubuntu-1250079-1793541520 / docker codex-kvpeer-alias2-1101 | /srv/opentallas-scratch2/claude/codex-kv-fn/peer_alias/eq_{mut,post,v}.log | RUNNING-HUNG(eq_v 21.7 h; eq_post 32.8 h; eq_mut 36 h) | No verdict. 3 yosys equiv_simple procs at ~300% CPU / 4 GiB, each with ~28 h CPU. Logs end mid-line in ezsat on u_coordinator__participant_token/cohort_tag | TOK-QW-3 | Started 11-01 05:58, before the window. It is alive and burning CPU, but logs are buffered and static. COORD decides whether to stop it. Sibling peer_struct finished earlier: post rc 0, mut rc 1, emitted_v rc 1
KV peer EQ alias-unkept | intel1 | oth-ubuntu-1751467-1793541773 / docker codex-kvpeer-alias-unkept-1101 | …/codex-kv-fn/peer_alias_unkept/ | RUNNING-HUNG(eq_v 21.8 h, eq_post 33 h) | No verdict. 3 yosys at ~285% CPU / 3.5 GiB | TOK-QW-3 | Same pattern as alias2
KV peer EQ nogroup | intel1 | oth-ubuntu-737955-1793540880 / docker codex-kvpeer-nogroup-1101 | …/codex-kv-fn/peer_nogroup/ | RUNNING-HUNG(eq_v 24 h, eq_post 32.8 h) | No verdict. 3 yosys at ~299% CPU / 3.8 GiB | TOK-QW-3 | Same pattern. Older containers dkv60-peereq-opt/s1 (40 h) and kv60res-fp-qkd_hr_core_peer (26 h) are also still up; I did not check them
KV norecipe qkd_hr_core_prompt EQ | intel1 | oth-ubuntu-783823-1793547550 / docker codex-kvfp-qkd_hr_core_prompt | /srv/opentallas-scratch2/claude/codex-kv-norecipe-1101/jobs/qkd_hr_core_prompt/fp/qkd_hr_core_prompt/ | RUNNING-HUNG(eq_post/eq_mut ~20 h, last write 11-01 22:06) | eq_v finished rc 0 (2712 s). eq_post and eq_mut still in ezsat on u_core.hc[177]. 2 yosys at 200% CPU / 1.2 GiB | DIE-KV-61 | Codex never mentions this job anywhere after 11-01; it looks orphaned
q2 forceA PRD | intel2 | oth-ubuntu-3505423-1793563799 (prd_run16.sh, docker) | /srv/opentallas-scratch2/claude/codex-kv-q2-1131/forceA/run_prd.log | RUNNING-progressing (log age 26 min) | DRT iteration 61 ("stubborn tiles"). Violations swing between 7 and 9 for the last ~5 iterations, 7.3 GB. prd_result.json still {"passes":[]} | DIE-KV-61 | Running 30 h with violations not converging. Codex left it "untouched"
q2 net11972-only repair | epyc2 | oth-ubuntu-896144-1793612360 | Epyc2 q2 repair dir | FAILED | exit 1: terminal DRC2, M2 track 13.185 shorts frozen M2_01674. Stopped before finish/STA as ordered | DIE-KV-61 | UP48 census 70efaa5cd: all 819 functional contacts lost, recorded as a negative. No successor
HHP kv3_pc place r5 (gen_r5_r8decl) | epyc2 | oth-ubuntu-3134028-1793603858; local ot-run client pid 793327 (19 h) | /srv/opentallas-scratch2/claude/codex-kv-hhp-place-2042/gen_r5_r8decl/kv3_pc__cl5a95b461/{run_place.log,lec/} | RUNNING-progressing (sidecar LEC only; newest file 43 min) | PLACE already FAILED at 23:24: OT_NATIVE_CELL_CAP 903118 > 400000. Only the async LEC on the synth netlist is alive, at hyp21 (~45 min per hyp, 22 failed-hyp files) | DIE-KV-61 | PLACE cannot proceed; the LEC result carries no physical credit. COORD may stop it. Holding a 32GB/4T slot
PC finalizer (Signal11 re-run) | epyc2 | oth-ubuntu-968496-1793612841 | Epyc2 codex-pc-reload-0018/finalize | FAILED | exit 2 at 03:24: post API mismatch after route. Route+finish done; 4261 clock nets / 48012 instances exact | DIE-KV-61 | Superseded by the post-only run below
PC post-only | intel1 | oth-ubuntu-4137542-1793621921 | /srv/opentallas-scratch2/claude/codex-pc-post-0355 | FINISHED | NOT SIGNED: TT −15.30 / 24 endpoints, FF +8.07, slew 100/31, cap 0, DRC 0, ANT 0, PG 1545314 / 0 open | DIE-KV-61 | Root cause is net41987 (187.8 µm)
PC unprotected repair attempt | intel2 | oth-ubuntu-3352862-1793628244 | codex-pc-geo80-birth-1102 | FAILED | exit 137: stopped in its own process before PRD (native PG begin was not installed) | FLOW-22 | Raw diagnostic only
PC protected early-native-PG repair | intel2 | oth-ubuntu-234293-1793632642 | /srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102/repair | FINISHED | PASS exit 0. 63 creates / 22 swaps / 126 bound; PG 447822 / 0; clock unchanged | DIE-KV-61 | 
PC DPL + dataGRT only (phase2) | intel2 | oth-ubuntu-1423278-1793637022 | /srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102/grt_only/{RESULT,fresh_grt.log,SAVED_GRT_PG_AUDIT.json} | FINISHED | PASS exit 0 at 08:59. RESULT says DPL_DATA_GRT_COMPLETE_REOPENED_PG_PASS_NOT_SIGNED. DPL 0 illegal, 22.9 µm total move; GRT 0 overflow, 11.04% usage, 1661463 µm; PG 447822 / 0 fail; clock diff PASS (4261 / 48012 unchanged) | DIE-KV-61 | Codex never collected this. A Claude lane has since launched the DRT successor: intel2 unit oth-ubuntu-370699-1793671029 at 17:57 (launch_guarded_drt.sh → drt_only/). Do not duplicate it
PC original fmx / r27c proofs | epyc2 | children (terminal) | receipts codex/pvb-tt-drv-0108@695dd212b | FINISHED | fmx EQUIVALENT 90951/90951. r27c NOT_EQ 49655/49656 (static_cmd[7] vs active_row[6]). fmxsmin EQ 90959. Lemma f28436ad1 PASS | DIE-KV-61 | r27c composite receipt is 1caa9398d
AHUB maxwire80 DRV repair | intel1 | oth-ubuntu-363419-1793623203 | /srv/opentallas-scratch2/claude/codex-ahub-maxwire80-1102/m10_maxwire80/{signoff.log,signoff/signoff.json}, collection/ACTUAL_BUFFER_ROUTE_COMPARISON.json | FINISHED | NOT SIGNED (exit 1 at 09:15). TT setup +22.51, FF hold +5.42, slew 0/0, cap 0, DRC 0, ANT 0, pin 631/631, PG open 0. The only failing gate is clock NOT RUN (UNEXPANDED_CHILD_ETM) | DIE-KV-61 | Codex never collected this. All DRV is closed now (was slew 3/2). Native birth was UNPROTECTED, so it gets no before-RC credit. The expanded child clock model is the only blocker
AHUB CG r2 / DRV-only predecessor | epyc2 | terminal | Epyc2 codex-kv-ahub-cg-2310/{Gm10_guard_r2,post_r3_interior} | FINISHED | route DRC 0 / ANT 0. Post: TT +12.49 / FF +5.42, slew 3/2. DRV-only run: TT +7.02 / FF +5.42 | DIE-KV-61 | Superseded by maxwire80
PV B t10 | epyc2 | oth-ubuntu-701975-1793611164 | /srv/opentallas-scratch2/claude/codex-pvb-tt-0108/t10 | FINISHED | NOT SIGNED: TT +51.18 / FF +10.39, slew 6/2, DRC 0 | DIE-QC-63 | Superseded by w80
PV B w80 + own final LEC + clock capture | epyc2 / intel1 | 1448517-1793616352 (exit 0); LEC 1859276-1793619673 (exit 0); clock capture intel1 3501907-1793619800 (exit 0) | Intel1 /srv/opentallas-scratch2/claude/codex-pvb-tt-0108/native_view_w80_superset/ot_qwen_tp8_pv_join_t | FINISHED | physical SIGNED: TT +51.16 / FF +10.36, DRV 0, DRC 0, ANT 0, clock 0 diff. Own final EQ 18181/18181. Export complete (15939 endpoints / 319803 pairs) | ROOT-MERGE-22 / SIGNOFF-SPRINT-21 | READY 6f1ba3b70. Needs merge and count
PV A p2W / p2D | epyc2 | terminal | ea6c202cb results | FINISHED | NOT SIGNED. p2W: TT +53.51 / FF −4.19 (1 endpoint). p2D: TT +50.31 / FF +0.88, slew 41/7 | DIE-QC-63 | No repair planned (same core as PV B)
PHY NRA kv3_phy | intel1 | docker kv60pvq-phy-nra-kv3_phy (20 h) | /srv/opentallas-scratch2/claude/die-kv-60/pvq/phyD_kv3_phy/stage/grt_client.log | RUNNING-progressing | BC hold repair at iteration 4020, 14098 buffers, WNS −96.6 (was −162.9 at ~1120), TNS −58580. 13.3/16 GiB | DIE-KV-61 | Close to its memory cap
PHY NRA kv3_phy_v1 | intel1 | docker kv60pvq-phy-nra-kv3_phy_v1 (20 h) | …/phyD_kv3_phy_v1/stage/grt_client.log | RUNNING-progressing (stalled metric) | Iteration 4080, 13836 buffers, WNS flat at −183.440, TNS improving slowly | DIE-KV-61 | WNS endpoint stuck on u_cland_ft0_i ring s_d[3][1]. Candidate for a COORD stop
CTL repack r3 PLACE | intel1 | oth-ubuntu-1572905-1793613300 | /srv/opentallas-scratch2/claude/codex-kv-ctl-repack-r3-0130/place.log | FAILED | exit 2: DPL-0033 detailed placement check failed (GPL had reached overflow .3336) | DIE-KV-61 | 
CTL DPL-only sidecar | intel1 | oth-ubuntu-2511770-1793616365 | CTL sidecar (8363e8914) | FINISHED | PASS exit 0. 18768 FF in rows, maxR2R 391.61 / 0 far, pin p90 15.92. Fill .0896, empty .7621: still on HOLD | DIE-KV-61 | 
CTL compact250 FP-only | intel1 | controller codex-kv-ctl-compact250-fp-0450 | /srv/opentallas-scratch2/claude/codex-kv-ctl-compact250-0430/{fp1,fp2,pg_retry} | FINISHED | fp1 guard AssertionError (no 2_ stages). fp2 FP completed (2_floorplan.odb); pg_retry dump: 2008 rows, 18768 FF, 6 macros | DIE-KV-61 | Superseded by the 233.28×302.4 PREP (local PG H1.715 / V1.700 HOLD). No GEN/FP/PLACE job
HG9 q1 SYNTH | intel1 | oth-ubuntu-3267841-1793633739 (shell 3232165 = NO_SYNTH_EXECUTED) | codex-hg9-q1-synth-0750/RESULT.json | FINISHED | PASS: 21931 instances (21927 std + 4 SRAM), 9785 seq | DIE-KV-61 | READY f4eabe71d
HG9 q1 official source→SYNTH proof | intel1 | oth-ubuntu-3474197-1793634582 | /srv/opentallas-scratch2/claude/codex-hg9-q1-lec-0820/proof/lec.json | FINISHED | EQUIVALENT exit 0 at 10:55. 19533 compare points; 10325 key points; 1184 register pairs; 4476 constant registers; t_total 11147 s; 18 hyp rounds | DIE-KV-61 | Codex never collected this. The old 82-DIFF result is now superseded by this proof of the current q1
TT_C fresh-source SYNTH | intel1 | oth-ubuntu-2659396-1793631363 | /srv/opentallas-scratch2/claude/codex-tt-locality-1102/synth_join_prep | FINISHED | PASS exit 0. The native join that followed (2949741) exited 1, FAIL_CLOSED (23 anonymous names, 244 masters). SAT 3390831 PASS | DIE-QC-63 | Census 7138f11f0
TT_C 87-cell joint row solve | intel1 | oth-ubuntu-550012-1793623734 | codex-tt-locality-1102/rowprep_v3/terminal_oom_journal.log | FAILED | exit 137: MEMCG-OOM at 4 GiB, 08:49 | DIE-QC-63 | Codex said "active, preserved" at 08:24; it OOMed 25 min later
TT_C rowprep_feasible v4 / target100_fresh v5 | intel1 | oth-ubuntu-192653-1793638318; oth-ubuntu-469823-1793639462 (both exit 2) | codex-tt-locality-1102/rowprep_v4_feasible, rowprep_v5_target100_fresh/rowjoint_report.json | FINISHED | Both FINITE_COMPONENT_INFEASIBLE (HiGHS infeasible): v4 87 vars, collisions 123→167; v5 100 vars, collisions 136→166. Diagnosis JSONs written 09:04 and 09:19. global_infeasibility_claim false | DIE-QC-63 | Launched after Codex stopped (08:51 and 09:11) by Codex children. Not reported anywhere
Causal RES2→RED→ROOT→H r1 (Epyc2) | epyc2 | oth-ubuntu-1529107-1793617086 | Epyc2 runtime/failure_ideal_oracle | FAILED | exit 1: ideal oracle 3d000000 vs actual 3cffffff. The oracle was wrong, fixed in 8b930f3ea | TOK-QW-3 | 
Causal retry3 | intel1 | oth-ubuntu-270641-1793622914 | /srv/opentallas-scratch2/claude/codex-causal-res2-root-head-0310; receipt results/token_pass/qwen_causal_res2_root_head_1102 | FINISHED | PASS exit 0: 4 users / 48 kernels / 128 partials / 4 RSTD / 1024 H; 3 controls caught; 10.3 GiB, 4559 s | TOK-QW-3 | READY 95a67d4d3
Native ME leaf gate packet3 | epyc2 | oth-ubuntu-2176313-1793622913 | Epyc2 ME packet3 | FAILED | exit 1: fixture compared K0 against K7 (bench bug, predicted) | TOK-QW-3 | Superseded by the packet4 PASS
Native ME four-chunk numerical | intel1/epyc2 | terminal | ME packet4 | FINISHED | PASS: 1600 reads / 3200 final-K values; wrong-weight control caught | TOK-QW-3 | READY 8b597f35c
ME read-only prefix capture | intel1 | oth-ubuntu-2046540-1793628803 | prefix capture | FINISHED | PASS exit 0: 1600 vectors / 25600 words, sha c3db0dda… | TOK-QW-3 | READY 6742ae10a
Native post HEAD gate | intel1 | oth-ubuntu-2875333-1793632218 | native post packet | FINISHED | PASS exit 0: 176 scalars, 16 reset contexts; wrong-scale control caught | TOK-QW-3 | READY 9e2427a8c
Tagged AMAX NU4 | intel1 | oth-ubuntu-3200594-1793633473 | AMAX packet2 | FINISHED | PASS exit 0: 4 users, candidates idx 11/30/36/63; MUT2/3/4 caught | TOK-QW-3 | READY a1b60a0c6
B-pilot macro→PART1 | intel1 | oth-ubuntu-3651382-1793635280 | B-pilot (frozen b9b91511 / d4c791529) | FINISHED | FULL PASS exit 0: 128 raw vectors incl. 40 pads; wrong address and wrong cycle caught | TOK-QW-3 | READY receipt still pending. The 256-context scaled job was never launched
HEAD GME control replay | epyc2 | oth-ubuntu-814367-1793611796 | /srv/opentallas-scratch2/claude/codex-head-gme-control-input4 | FINISHED | PASS: 11 cases | TOK-QW-3 | READY 7ce84273c
HEAD XPF control | epyc2 | oth-ubuntu-1011667-1793613168 | codex-head-xpf37-control-packet1 | FINISHED | PASS: 12 calls | TOK-QW-3 | READY 545953d93
HEAD WTN input-only replay | epyc2 | oth-ubuntu-4020491-1793609695 | Epyc2 scratch2 | FINISHED | PASS: 49 cases | TOK-QW-3 | READY 772fed27c / 9e518a517
NF2 reset-polarity negative 16GB | epyc2 | oth-ubuntu-1083624-1793613612 | codex/nf2-disabled-preview-2345 | FINISHED | PASS exit 0: decisive negative (mutant fault 1 vs reference 0) | DIE-KV-61 | READY 79af8397d
RECIP native FP | intel2 | oth-ubuntu-2961941-1793626634 (+ ODB reader 3013929) | /srv/opentallas-scratch2/claude/codex-recip-native-fp-0640 | FINISHED | PASS exit 0 | DIE-KV-61 | READY 121caa760. Intel1 waiter 1342245 never admitted (NOTRUN)
RECIP private PLACE canary | intel2 | oth-ubuntu-413122-1793633354 | codex-recip-place-canary-prep-0810 | FINISHED | PASS exit 0: native GPL first attempt; PG audit 106210 / 0 fail; +628 buffers | DIE-KV-61 | READY d43e0a057. CTS lifecycle is PREP only (36422143f); no CTS job
ZH native FP | intel2 | oth-ubuntu-3816364-1793630163 (+ reader 3844631) | codex-zh-native-fp-prep-0705 | FINISHED | PASS exit 0: 268 south pins | DIE-KV-61 | READY 2245d697b. ZH PLACE not launched
hroot inherited geomr_count / countb / event28w_c geom50 | intel1 | inherited | geometry_disk collection | FINISHED | FAIL: COUNT overflow 9552 / 3 far, COUNTB 8271 / 2 far | GEOM-110 | Codex reports these collected. Current 65FF witness is PREP only
SOURCE13 parent frontend | intel1 | terminal | /srv/opentallas-scratch2/claude/codex-source13-top-0010/linked_native/frontend8 | FINISHED | PASS: 4.92 s, 262 CPP. The original B2o top had OOMed | TOK-HBM-1 | READY 431927330 + 0cdd5c51c
Old NOWAIT B (veh60-nwB) | intel1 | sim 3025369 (gone) | /srv/opentallas-scratch2/claude/kv-fn-7/veh60/runs/tok_gen1_nwB/nwB/{verdict,sim.log} | FINISHED | FAIL: boot PASS, layers 0/36 (expected, old consumer bug). exit 0 at 02:12, 20509 s wall | TOK-QW-3 | Diagnostic only
Old NOWAIT A (kvfn7-e2-fullA) | epyc2 | controller 954796 (gone) | kv-fn-7/veh60g1/b | UNKNOWN | No Vtb_kvslice process on epyc2 and no output after 11-01 20:00 found | TOK-QW-3 | Diagnostic only

**READY items** (copied from the files)
- KV credit fix 9e4f17154 (root integrated); native KV programme reuse 1c504a86c; HGI coupon 5dd4dfe6c
- HEAD: RES2 ff04db62b; HEAD37 77576b626 / 64c8e29ec; CTLM37 e0ae07be2; ROOT prearm d339c3c0b; native H 4e5521b06; WTN 772fed27c + 9e518a517; GME 7ce84273c; XPF 545953d93; S8 PREP 68f56e2ee; frontage 0c430bc2c; native post 9e2427a8c (source e238e0b1a); six-part loader 778d13ecf; AMAX a1b60a0c6
- codex/qwen-causal-root-0300: 2d90a2790, bb70b6dca, 8b930f3ea, 95a67d4d3 (final PASS)
- Native ME 8b597f35c; prefix capture 6742ae10a; reference f7a92f80e
- codex/hbm-top-link-0015: c01e8d80a, 468710c02, 8c64782b4, final 431927330 + 0cdd5c51c
- codex/kv-pc-reload-checkpoint-0020: 52eb2ffcc → a2c61e031 → e14242c55 → f1f5051d7, f28436ad1, 1caa9398d. PC post e62321b46 / e6cdeef32; early-PG e8be4a36c / 3dfef7420; repair 655fd9284; phase2 722d7d7e4; DPL/GRT PREP 34b832c5f; wrapper review 1b9177e11
- HHP: 487c85951 + ea246756a, ef181ca6a; codex/hhp-model-projection-0315 adcf4e3b6; c7abb4874; codex/hhp-ft-roles-0435 7346acc5f, 06e44f167 / 4ce8b919c; codex/hhp-historical-boundary-0600 01484262b; mesh certifier 2f9cde5b6 / ff98807fa; interface join 31657efe8; 4-SRAM PREP 5afe3ec66
- AHUB: identity fb088fd94; maxwire80 f0e534374; codex/ahub-selected-child-rebuild-prep-0630 a5d5494d4
- codex/nf2-disabled-preview-2345: 8d6b45e85, 31ce188a4, 79af8397d
- PV: codex/pvb-tt-drv-0108 d0418b5a0 / 06bf81510, 427c3090d / 695dd212b, 6755429c7, ee4274dab, 92ae91ba9, ea6c202cb, 79b8fe891; codex/pv-export-reader-0405 6f1ba3b70 (reader 813a380fc)
- q2: 1810675a6 / f26c66047; census 70efaa5cd
- CTL: 2158969ec, fb088fd94, 8363e8914, 543abd2df, metadata 44814db6
- Q6: 362dd8ed9; codex/q6-geometry-0215 6840b5c82, a60c43a7f, a7f357a7f
- RECIP: codex/recip-native-fp-0640 865c16e31 / 121caa760; c8dfd649d, 3f3d236af, d8c783424; codex/recip-place-pg-canary-prep-0810 752ebe7af, 94238c211, ab13b5308; PLACE d43e0a057; proof join fc66a4d6d; CTS PREP 36422143f
- ZH FP 2245d697b. PG: codex/pg-gpl-admission-1102 728a529a0 (not merged)
- HG9 q1 SYNTH f4eabe71d
- TT_C: bb03aa5f3, bed068146; codex/tt-locality-prep-1102 a7ebca003, 7138f11f0, c570fe8ee
- codex/geom-1101: 0a7ea64e1, 28ea9012b, 1962a25ca, 947051798; parent residual 22b0de11c

### E. HBM / geometry (subagent). Update 18:46: gql_d26 finish 77895/77929 are already inactive (ended by another lane); the S81 bridge SYNTH was stopped as W1
job_id | host | unit/container/controller | path (result dir/log) | state | result | owner_lane | note
ROOT clock batch resume (corrected, ROOT_BATCH) | intel1 | oth-ubuntu-1620213-1793613458, py PID 1624942. The local ot-run ssh client PID 1164733 (started 01:57:18) is this job's client: it was admitted at once and is not waiting | intel1 /srv/opentallas-scratch2/claude/codex-hbm-root-batch-resume-0150/{batch.log,batch.err,checkpoint_HELD*.json} | RUNNING-progressing | MOVE 162 (138 MOVE lines). Empty names 147→12. Metric (0,0.0,12): 0 over-radius, 0 overload. RSS 499 MB of 2 GB. batch.err is empty. checkpoint_HELD audit: HELD_INCOMPLETE, 160 moves. No candidate_PASS/audit_PASS yet | DIE-HBM-58 | batch.log last written 17:55. Elapsed 16h13 with 16h02 CPU. Codex's 07:51 note had "B119 moves/55 empty"
ROOT clock A (original minimal-2355) | intel1 | oth-ubuntu-3566194-1793606281, PID 3578309 | intel1 .../codex-hbm-root-minimal-2355/ (it alone owns clock_candidate/clock_result/root_type_clock.json); log intel2 /tmp/codex-hbm-root-minimal-clock-2355.otrun.log | RUNNING-progressing (slow) | Iteration 27, score (0,0,147,0.0): 147 empty, 0 radius/cap failures. No clock_result.json yet | DIE-HBM-58 | Log last written 17:08, about 1 h old. Elapsed 18h12. A_vs_B_input_identity.json says inputs are identical to the batch job apart from the root clock. Do not overwrite its outputs
ROOT FT joint L9m retry (ft-joint-2220) | intel1 | oth-ubuntu-1012495-1793600622 (PID 1044388) | intel1 .../codex-hbm-root-ft-joint-2220/repair_result.json | FINISHED exit 0 (11-02 02:10) | PASS: all 14 slots, 0 added cycles. L9mx1, L4x1 and L4mx1 max hop 405.00 µm (exactly at the limit). L9x1 390.69, L700/L701 about 284 | DIE-HBM-58 | Codex's checkpoint still listed it as CPU-active; collect it
final17 global census | intel1 | – | .../codex-hbm-final17-0035/{tools,census.py} | NOT-RUN | Staged only. Waits for a frozen ROOT clock PASS | DIE-HBM-58 | Copy the selected PASS into this isolated directory
gql_d26 finish 7e7e2a | intel1 | oth-ubuntu-77895-1793345168, container hbmcore-ot_hgi_coll_gq_land_7e7e2aef40e2-_codex2315d26_7e7e2a_-78670 | intel1 .../codex-hbm-cores-2249/gql_d26/kits/ot_hgi_coll_gq_land_7e7e2aef40e2-_codex2315d26_7e7e2a/run_finish.log | RUNNING-HUNG (22.6 h) | DRT stuck at the 58th optimization iteration; last pass had 565 violations. Started 10-30 00:26 | DIE-HBM-58 | run_finish.log last written 11-01 19:37. Still 100% CPU, 12 GiB/40 GiB. No progress. COORD decides
gql_d26 finish 068dba | intel1 | oth-ubuntu-77929-1793345168, container hbmcore-ot_hgi_coll_gq_land_068dba88be63-_codex2315d26_068dba_-79574 | same base, kits/ot_hgi_coll_gq_land_068dba88be63-.../run_finish.log | RUNNING-HUNG (18 h) | DRT stuck at the 58th optimization iteration; last pass had 454 violations | DIE-HBM-58 | run_finish.log last written 11-02 00:14. 200% CPU, 11.6 GiB. Never collected
pslice_c5 attempt_4 geom GRT | intel2 | oth-ubuntu-744403-1793589753, container ap-ageom-kw-ot-hbm-su-programme-pslice-c5-grt-1366459 | intel2 /srv/opentallas-scratch2/claude/kit-wave/hbm/d44o/items/ot_hbm_su_programme_pslice_c5/attempt_4/geom/grt.log | RUNNING-progressing (very slow) | GRT extra iteration 27/50. Started 11-01 22:22 | KW-FIX-1 (DIE-HBM-58 consumer) | grt.log updated 18:29, 99% CPU, 3.3 GiB. At this rate roughly 17 h more. This is legacy C5, not the real r10 producer
PSlice tx3 PLACE retry 0400 | intel2 | – | .../codex-pslice-tx3-place-retry-0400/PLACE.log | FAILED | MPL-0020 at macro_place (2_2_floorplan_macro). Kit LEC EQUIVALENT | DIE-HBM-58 | Terminal 05:09. Codex still called PSlice "live" at 07:51
PSlice trunk-join 0425 | intel2 | oth-ubuntu-128328-1793632178 | .../codex-pslice-trunk-join-0425/{controller.log,kit/lec/lec.json} | FINISHED exit 0 | LEC EQUIVALENT (top pslice_c5, 1857 s) | DIE-HBM-58 | –
StoreA official LEC 0120 (12 GB) | intel2 | oth-ubuntu-1993393-1793611200, controller codex-storeA-native-lec-0120.service | .../codex-storeA-native-lec-0120/lec/lec.json | FINISHED exit 2 (04:05) | UNPROVEN: 128 compare points depend on X sources. Not a mismatch | TOK-HBM-1 | Replaced by the 0435 run
StoreA cubes LEC 0435 | intel2 | oth-ubuntu-1885065-1793622537 | .../codex-storeA-native-cubes-0435/lec/lec.json | FINISHED exit 0 (04:43) | PASS: EQUIVALENT, 25760/25760 per the log, 855.7 s | TOK-HBM-1 | READY 28ea41ddd
StoreA regional4 sourceproof 1000 | intel2 | – | .../codex-storeA-regional-native-1000/{SOURCEPROOF.log,kits/*regional4_captured*/lec/lec.json} | FINISHED | UNPROVEN: the same 128 X-dependent points | TOK-HBM-1 | Started after Codex's 08:24 stop (08:47, terminal 11:13). Nothing in the files mentions it
StoreB sourceproof 0210 | intel2 | – | .../codex-storeB-native-sourceproof-0210/sourceproof_result.json | FINISHED | FAIL / official UNPROVEN: 128 X points, 9180 s | TOK-HBM-1 | –
StoreB cubes 0535 | intel2 | – | .../codex-storeB-native-cubes-0535/lec/lec.json | FINISHED | PASS: EQUIVALENT, 723.6 s. Log gives 28503 EQ | TOK-HBM-1 | Receipt 7bf6ec66f. StoreB GEN capsule (a4ac2f2df) was never dispatched: NOT-RUN
Programme r10 LEC 0448/0452 | intel2 | – | .../codex-programme-native-0448/kits/*source_eq/lec/lec.json | FAILED | UNPROVEN: yosys lint failed (Slang lint OOM at 12 GB) | TOK-HBM-1 | Primitive-boundary fix is with FLOW
Programme r10 native_boundary 0525 | intel2 | – | .../codex-programme-native-0525/kits/*native_boundary/lec/lec.json | FINISHED | PASS: EQUIVALENT, 572.7 s. Log gives 56061 EQ | TOK-HBM-1 | b71490613
Programme postSYNTH EQ 0605 | intel2 | – | .../codex-programme-postsynth-EQ-0605/lec/lec.json | FINISHED | PASS: EQUIVALENT. Log gives 54439 EQ | TOK-HBM-1 | f57b773ae
Programme native 0835 / 0845 / current-0905 | intel2 | – | .../codex-programme-native-{0835,0845,current-0905} | FINISHED | 0835 GEN rc=1 (FAIL). 0845 GEN rc=0. current-0905 proof_0920 EQUIVALENT (08:50) | TOK-HBM-1 | All after 08:24 and not in any handoff
Programme clock final 0800 | intel2 | – | .../codex-programme-clock-final-0800/source_Y_scope_failure.json | FINISHED | FAIL_ACTUAL_OUTPUT_PIN_220_SCOPE: max Y→CLK 220.899 µm (regional_0, regional_4) | DIE-HBM-58 | Model only. Later companions in clock-pin-0810 and clock-components-0910
HCOL head5 sourceproof 0205 | intel2 | controller PID 2820721 (gone) | .../codex-hbm-hcol-head5-sourceproof-0205/out/ | FINISHED | PASS: 1404 positive / 0 differences; 1116 expected mutant differences | TOK-HBM-1 | b7a86093a. Source-only
HCOL565 native h0 r3 | intel2 | oth-ubuntu-785315-1793634785 | .../codex-hcol565-native-h0-r3-0810/gen/*regional565_native4/{FAIL_PREFLOOR,lec/lec.json} | FAILED exit 3 | LEC NOT EQUIVALENT: 117 differences (g_add.u_a.g_lat.u.err[1] FFs) | DIE-HBM-58 | Terminal about 09:34, after 08:24. Unreported
HCOL565 native h1 r3 | intel2 | oth-ubuntu-785320-1793634785 | .../codex-hcol565-native-h1-r3-0810/... | FAILED exit 3 | LEC NOT EQUIVALENT: 16 differences (same err[1] class) | DIE-HBM-58 | Terminal about 09:42. Unreported
DRT readout NW_v2 | epyc2 | oth-ubuntu-1106817-1793613746 | intel2 /srv/opentallas-scratch2/claude/codex-hbm-drt-readout-2125/NW_v2/{TT,FF} | FINISHED exit 0 | PASS: READOUT_COMPLETE, missing 0 | DIE-HBM-58 | 287b4bcfd
DRT readout NW_v1 | intel1 | oth-ubuntu-971269-1793624909 | .../drt-readout-2125/NW_v1 | FINISHED exit 0 (05:08) | PASS: READOUT_COMPLETE, OT_RECOVERY_DONE missing=0. Source DRT EXIT 139 (expected) | DIE-HBM-58 | Never collected
DRT readout NE_v1 | intel1 | oth-ubuntu-3843781-1793655137 | .../drt-readout-2125/NE_v1 | FINISHED exit 0 (13:32) | PASS: READOUT_COMPLETE, missing=0 | DIE-HBM-58 | Never collected
DRT readout NE_v2 | intel2 (collector) / intel1 (source DRT) | collector PID 207614 is in its sleep loop; source container clkloc7-drt-NE_v2, 13 h | intel1 /srv/opentallas-scratch2/claude/hbm-clkloc-7/drc/NE_v2/drt.log | RUNNING-progressing | Source DRT at 70% with 104 violations, 124.7 GB. Collector waits for "EXIT" | DIE-HBM-58 | drt.log updated 18:20
Tnode target235 route-only 0010 | epyc2 | – | .../codex-hbm-tnode-target235-routeonly-0010/RESULT.json | FINISHED | GRT overflow 0. TT 251.75 / FF 199.26 bands PASS. FF hold −72.46 (class unknown) | DIE-HBM-58 | 159a307e2
Tnode normal GRT+hold 0430 | intel1 | oth-ubuntu-806872-1793624456 | .../codex-tnode-normal-grt-hold-0430/RESULT.json | FINISHED exit 0 (05:20) | PASS: TT setup +91.64 / hold +26.29. FF setup +306.23 / hold +6.61. 0 violating hold endpoints. PG 31224/0. Clock guard PASS | DIE-HBM-58 | SIGNED false
Tnode post-repair route-only 0510 | intel2 | oth-ubuntu-3091502-1793627145 (controller 3090919, gone) | .../codex-tnode-final-postrepair-routeonly-0510/{RESULT.json,JOIN.json} | FINISHED exit 0 | GRT0, 15200 nets. TT setup +90.47 / hold +25.09. FF hold +4.79 per the geometry file. PG 31224/0 | DIE-HBM-58 | –
Tnode observational DRT 568 | intel2 | oth-ubuntu-319272-1793632983 (controller 318382, gone) | .../codex-tnode-drt-prep-0620/RESULT.json | FINISHED exit 0 (07:57) | PASS: DRC 0, antenna 0, 164963 µm wire / 144806 vias, M2–M5. 0 creates/swaps. PG 31224/0 | DIE-HBM-58 | 465b031be. No routed RC, fill or SIGNED yet
Tnode fill prep 0910 / r2 1000 | intel2 | oth-ubuntu-1918998-1793638988 / oth-ubuntu-2167469-1793639956 | .../codex-tnode-fill-prep-0910, ...-fill-r2-prep-1000 | FINISHED | 0910 exit 2 (FAIL). r2 exit 0 (prepare only) | DIE-HBM-58 | After 08:24, unreported
BFQG guide PG fix 0200 | epyc2 | oth-ubuntu-1346810-1793615494 | .../codex-bfqg-guide-pgfix-0200/RESULT.json | FINISHED exit 0 | PASS: PG-only repair, 32782/0 open | DIE-HBM-58 | Checkpoint called it unlaunched; it did run
BFQG corrected route-only r2 0230 | epyc2 | – | .../codex-bfqg-corrected-routeonly-r2-0230/RESULT.json | FINISHED | RAW_CONGESTION_PASS: overflow 0, 20 clock nets, PG 32782/0. 9 registration failures held. G7 proxy channel_v 1.04 still HARD FAIL | DIE-HBM-58 | Classifier OWNER? pending (c8ae2d820)
SPU current50 GRT | intel1 | – | .../codex-spu-current50-0355/grt.json | FINISHED | PASS: total overflow 0, 17 slots, max 371.25 | DIE-HBM-58 | Prototype only
CTL native4 LEC 0510 | intel1 | oth-ubuntu-873068-1793624631 | .../codex-hbm-ctl-native-lec-0510/lec/lec.json | FINISHED exit 0 (06:20) | PASS: EQUIVALENT, 41377/41377 per the log, reset 4 | TOK-HBM-1 / DIE-HBM-58 | 39442d65d. Earlier sourceproof-0455 FAIL_PREFLOOR (face_guard) preserved
HF static sourceproof r2 | intel2 | oth-ubuntu-1719847-1793621979 | .../codex-hfdep-static-sourceproof-r2-0330/gen/*/FAIL_PREFLOOR | FAILED exit 3 (04:21) | FAIL_PREFLOOR face_guard | DIE-HBM-58 | Superseded by the next row
HF fc9 sourceproof 0640 | intel2 | – | .../codex-hfdep-fc9-sourceproof-0640/gen/*/lec/lec.json | FINISHED | PASS: EQUIVALENT. Miter VLT 18200 checks, 0 diff, mutant caught | DIE-HBM-58 | native4-lec-0340 was NOT_EQ (2 fault_cause bits)
VM calendar dates 0830 | intel2 | – | .../codex-hbm-vm-calendar-dates-0830/compile_write.log | FAILED | tb_write.sv:3 syntax error. result*.log exist for an earlier pass | TOK-HBM-1 | After 08:24. fcce08d2d covers the earlier diagnostic
S81 whole-KV bridge SYNTH | intel2 | oth-ubuntu-1159241-1793599785, container codex-kvbridge-size-2111-1181066 | intel2 .../codex-s81-kvbridge-size-2111/synth.log | RUNNING-HUNG (15 h) | Yosys stuck in 3.15 SHARE (SAT resource sharing). No synth_exit or mapped_count | DIE-S81-48 | synth.log last written 03:28. 100% CPU, 24.1/32 GiB. Never use the 358423 fallback count. COORD decides
S81 parent residual SYNTH | epyc2 | oth-ubuntu-1063615-1793613514 | .../codex-s81-parent-residual-0148/ | FAILED exit 2 | Outer synth_odb fails on missing LEF for the 24 alias cuts. Mapped: 500877 std cells, 24/24 cuts, 4 SRAM. Peak 4.37 GiB | DIE-S81-48 | Count only. 22b0de11c
Hroot FF-only PLACE | epyc2 | oth-ubuntu-3429395-1793605511 | .../codex-hroot-ff-place-2338 | FINISHED exit 0 | Col 3.691→2.826 (still FAIL). All 19 r2r failures unchanged, max 1010.34 | DIE-KV-61 | –
Hroot input PG audit + repair | epyc2 | audit oth-ubuntu-1246714-1793614714 (exit 2, found opens); repair oth-ubuntu-1384514-1793615786 | .../codex-hroot-input-pg-0205/hroot_pg_bound.odb | FINISHED exit 0 | PASS: 27094 opens bound, then 426814/0 open | DIE-KV-61 | Chunk COMB capsule NOT_DISPATCHABLE
Hroot inherited GRT g2 / event28w_c / count / countb | intel1 | old containers, including ap-ageom-kw-kv3-hroot-grt-3638353 (none running now) | geom100/kv_hroot_g2; kit-wave/qwen_kvsys/event28w_c/items/kv3_hroot/geom; die-kv-60/hroot3/geomr_count(b) | FINISHED | FAIL: overflow 9224 / 9224 / 9552 / 8271 | DIE-KV-61 | event28w_c final image/JSON still to collect
QC SC route probe / 3BUF import / SC49 import | epyc2 / epyc2 / intel1 | oth-ubuntu-4070850-1793609927 / oth-ubuntu-1067116-1793613522 / oth-ubuntu-309237-1793623037 | .../codex-qc-sc-red-1101/{sc_route_probe,sc_buffer_geometry,sc_batch_buffer_geometry} | FINISHED exit 0 | GRT0. 3BUF replay TT −388.81 / FF −163.48 (FAIL). SC49 geometry and guards PASS | DIE-QC-63 | Route+TT/FF after SC49 needs ROOT scope
QC L1 ordinary DRT | epyc2 | oth-ubuntu-3747083-1793607615 | .../codex-qc-l1-lvt-route2-0015/route.log | FAILED exit 2 (02:31) | DPL-0050 "No fillers found for LVTN" at 5_3_fillcell | DIE-QC-63 | Checkpoint still listed it as active
QC L7 full gate / paired TT/FF | intel1 | oth-ubuntu-2920748-1793632382 / oth-ubuntu-1086720-1793625281 | codex-l7-full-geom-prep-0735/result | FINISHED exit 0 | Gate PASS (r2r 336.2/0, PG 0). TT setup +0.19 / hold +9.09; FF hold +0.46 | DIE-QC-63 | cefe8648a
QC RED full GRT50 | – | not identified | QC owner | UNKNOWN | Released by QC owner after PG0. No receipt in my files | DIE-QC-63 | –
HEAD mesh_e | – | unit 94510 (no completion record on any host) | – | UNKNOWN | – | DIE-HEAD-54 | Named only as "preserved active"

READY items:
- codex/hbm-d44r-2039: 52ce95d3d lower-window PREP (superseded; needs scope correction e8a0b69d1 with it); 6c0e7a012 B001 tap; e8a0b69d1 union scope correction; 4aa0bb781 SU00 upper clocks; 0abfdcfac B113 restored-upper clocks; 5573067ad ROOT planner manifest; 55c26b902 NE SU31 complete type
- codex/clock-obstacle-union-2208: 8ebe2fe0e canonical clock-obstacle union; 6689ccd8c NE density; a1a9b4aec NW density; 4ac4830c8 default-OFF vector assignment
- codex/hbm-clock-recovery-1101: b88f49c82 six-type offsets; e0de9c3f3 Q101 repair
- codex/ft-obstacle-union-2149 (tip fc3495516): 1fc487ae9 FT union; a0f7f6179 reach legalizer; 6bcf3336b true-source provider packet; cab418a6d pricing baselines; fd69ac8bb native-cycle inventory; 38138c569 StoreA OOM/model; StoreB 7fb4ddfad/e56028b1b/a4ac2f2df (GEN capsule)/3f2132cb9; 37ab4198b programme frontier; fc3495516 programme image
- codex/hbm-tnode-compact-kit-1101: 159a307e2 target235 route-only
- codex/hbm-bfqg-compact-kit-1101: ef8244c55 PLACE/PG evidence; b6fb65e25 guide PREP
- codex/hbm-query-native-event-0135: e0fadbb7e, 6dcbdc449, 268e465bc QUERY source PREP
- codex/r2-reset-capture-1101: f04ea6025 typed reset/capture recognizer
- codex/hbm-hcol-regional-1101: 53b291069 regional simulation
- codex/hbm-mu1-frontier-1101: 59011edfa mu1 frontier
- codex/hbm-tail-index-main-1101: a340880d8 predecode slice (default-OFF)
- codex/hbm-token-2038: ddb21fe4c causal STK3/q0 component
- HBM token/source, branch not named: b7a86093a HCOL head5 sourceproof; 287b4bcfd NW_v2 readout; dc6e6c52e programme phase; 834797670 StoreA predecode correspondence; 831425dda r10 2904 ABI/model; 28ea41ddd StoreA 25760 EQ; 3dbad4ea4 programme LEC UNPROVEN record; cea5fc829 programme row candidate; 069066e68 StoreB B32 decoder PREP; 7bf6ec66f StoreB 28503 EQ; b71490613 programme 56061 EQ; f57b773ae postSYNTH 54439 EQ; 39442d65d CTL 41377 EQ; fcce08d2d VM stage diagnostic; 20cdd649d HCOL source event (disabled); 39a846337 mu1 frontier; 2c0ffc1ba occupied-row chain; e83b11071 conservative-seed diagnostic
- codex/geom-1101: 90df62574 (tip at checkpoint), 009d3d5e6 geom_rules 5_1_grt fix, 1962a25ca, bfa75d1f7, a2d0d5b8d (incl. 70eecd0ed), cdaca3143 (incl. e20438fcf), 3c86a35d5, d73a02e7b, c216ea8c8 (incl. 838f38683), cefe8648a L7 full gate, 465b031be Tnode DRT, 8838e2bb0 (programme/T51/PSlice + hroot 0830 fix); plus review records 8b63374c2, 13adcb682/fbb33932e (HCOL565 LOOK), 03457df82 (CapWEST2), 947051798/c8ae2d820 (BF classifier)
- codex/s81-kvleaf2-census-2058: 9b537aa4a census; 22b0de11c source sizing; 0fd42116b VN_b PREP (held)
- PC author: 31657efe8 PC source join

Key points:
- **Hung, needs a COORD call:** both gql_d26 DRT finishes, about 18–23 h with no progress, and the S81 whole-KV Yosys SHARE pass, 15 h silent.
- **Uncollected terminals:** L9m PASS, DRT readouts NW_v1/NE_v1, L1 DRT FAIL.
- **Codex activity after its stated 08:24 stop, up to 11:13:** HCOL565 r3 h0/h1 NOT_EQ, StoreA regional UNPROVEN, programme current-0905 EQ, Tnode fill prep jobs, VM calendar compile error. No handoff mentions these.
- **Still running and progressing:** both ROOT clock jobs (neither has a frozen PASS yet) and the NE_v2 source DRT.

## 4. Codex branches NOT on main (rechecked with merge-base --is-ancestor against intel2 origin/main 1770163a818 at 2026-11-02 18:54 PST): 77
Format: branch@tip, files changed vs main, code files, merge-tree result, code dirs. Results-only branches (code=0) are low-risk merges. CONFLICT ones need a rebase.
```
codex/hbm-tail-index-1101@fae432db5 files=20 code=3 CONFLICT tools/hbm_b2(1) rtl/hbm_accel(1) physical/die_plan(1) 
codex/qwen-headlink-2100@03143c430 files=15 code=5 clean tools/qwen_layerbench(5) 
codex/ds-native-pricing-2059@73cd5127f files=3 code=0 clean 
codex/hbm-mu1-frontier-1101@59011edfa files=8 code=0 clean 
codex/kv-ahub-fault-split-2050@c9ac8d1f7 files=12 code=1 clean physical/die_plan(1) 
codex/ds-ca-cb-2128@b6ce71c32 files=16 code=0 clean 
codex/s81-t48-cb-candidate-2138@d4632680a files=6 code=1 clean tools/s81_dv(1) 
codex/qc-sc-red-1101@60a009019 files=12 code=2 CONFLICT rtl/qwen_dv(2) 
codex/qc-nl-prefix-intake-1101@d38a85e23 files=5 code=0 clean 
codex/hbm-clock-recovery-1101@25d84831e files=17 code=4 clean tools/die_plan(4) 
codex/ds-bf-selectors-2200@16c3ac57d files=30 code=4 clean tools/s81_dv(4) 
codex/ds-bf-ranktags-2230@06ef2d7dd files=37 code=5 clean tools/s81_dv(5) 
codex/ds-current-link-ages-2240@d67d7d3f8 files=44 code=6 clean tools/s81_dv(6) 
codex/qc62-collect-1101@82190c1ff files=51 code=11 clean physical/die_plan(11) 
codex/kv-q2b-margin-edge-prep-2300@b427f8937 files=10 code=0 clean 
codex/kv-ahub-cg-guard-review-2317@07ecc6f73 files=14 code=0 clean 
codex/kv-hostcredit-2044@1c504a86c files=2 code=0 clean 
codex/qc-neighbor-counts-1101@c2b571529 files=14 code=0 clean 
codex/ttc-part-lemma-1101@578cdfef1 files=6 code=0 clean 
codex/reset-physical-controls-2340@5aafc2ea4 files=1 code=1 clean tools/autopilot(1) 
codex/hbm-hcol-regional-1101@53b291069 files=22 code=3 clean rtl/test(2) rtl/hdc(1) 
codex/head-collect-1101@9b4b5fe32 files=13 code=0 clean 
codex/wtn-head37-prep@10166fb77 files=6 code=4 CONFLICT tools/qwen_layerbench(2) rtl/test(1) rtl/qwen_dv(1) 
codex/qc-prefix-access-1102@ec0e8eb70 files=13 code=0 clean 
codex/head-ld-source-1102@0a99f6ca7 files=7 code=0 clean 
codex/vsw-publish-0130@fbc0b5c45 files=37 code=27 clean physical/ref_tile(27) 
codex/nf2-disabled-preview-2345@79af8397d files=51 code=1 clean physical/die_plan(1) 
codex/qc-nl-final50-1102@ae91422ab files=6 code=0 clean 
codex/hbm-d44r-2039@a0a7a9701 files=35 code=0 clean 
codex/r2-reset-optin-integration-0220@78edbd892 files=9 code=2 clean tools/autopilot(2) 
codex/head-export-continuity-1102@587c36275 files=9 code=3 clean tools/die_plan(3) 
codex/head-typed70-review-1102@078d029ad files=2 code=0 clean 
codex/hhp-model-projection-0315@adcf4e3b6 files=25 code=2 clean physical/die_plan(2) 
codex/pvb-tt-drv-0108@79b8fe891 files=32 code=1 clean tools/die_plan(1) 
codex/pv-export-reader-0405@6f1ba3b70 files=40 code=3 clean tools/autopilot(2) tools/die_plan(1) 
codex/qc-fdi-calendar-contract-0310@36e907e9d files=16 code=0 clean 
codex/hhp-ft-roles-0435@4ce8b919c files=50 code=2 clean physical/die_plan(2) 
codex/pc-residual-prep-0510@60b646f33 files=79 code=2 clean tests/test_kv_core_pin_audit.py(1) physical/die_plan(1) 
codex/hhp-historical-boundary-0600@01484262b files=81 code=4 clean physical/die_plan(4) 
codex/postcts-partition-binding-1102@43e49c51f files=79 code=5 clean tools/die_plan(5) 
codex/tnode-drt-prep-0620@568c66c50 files=11 code=0 clean 
codex/ahub-selected-child-rebuild-prep-0630@d8c783424 files=164 code=13 clean tools/qwen_layerbench(13) 
codex/zh-native-fp-prep-0705@2245d697b files=19 code=0 clean 
codex/hbm-bfqg-compact-kit-1101@46d2bbb36 files=55 code=2 clean tools/hbm_b2(2) 
codex/pslice-trunk-join-0425@62747890a files=11 code=4 clean physical/die_plan(4) 
codex/s81-kvleaf2-census-2058@0fd42116b files=16 code=0 clean 
codex/s81-source39-event-0800@8b93c6acc files=5 code=4 CONFLICT physical/die_plan(4) 
codex/hbm-obs136-0450@839b6437d files=27 code=1 clean rtl/hbm_accel(1) 
codex/hbm-hfdep-native-0250@46a4ed043 files=5 code=1 clean tools/hbm_b2(1) 
codex/qc-safe-land-0445@594c0dca0 files=27 code=0 clean 
codex/ap-reader-1102@c04ed5e71 files=4 code=3 clean tools/openroad_pg_birth(3) 
codex/pg-gpl-admission-1102@728a529a0 files=12 code=2 clean tools/openroad_pg_birth(1) physical/common_flow(1) 
codex/hbm-query-native-event-0135@4104ec76b files=152 code=5 CONFLICT tools/hbm_b2(4) physical/die_plan(1) 
codex/hg9-q1-current-0715@5afe3ec66 files=57 code=0 clean 
codex/pg-cts-prep-1102@1f478d9d4 files=9 code=0 clean 
codex/hbm-tnode-compact-kit-1101@337b9c429 files=77 code=1 clean physical/die_plan(1) 
codex/ft-obstacle-union-2149@1da9042d2 files=224 code=34 CONFLICT tools/hbm_b2(23) tools/hbm_layer_vehicle(7) physical/die_plan(3) 
codex/s81-nearmiss-2036@13e611922 files=283 code=0 clean 
codex/qc62-ucie-held-1101@b7856db5f files=266 code=11 clean physical/die_plan(11) 
codex/hbm-ctl-native-0440@c55bc2d8b files=56 code=1 clean tools/hbm_b2(1) 
codex/g0c-regress-1101@274f9ecb9 files=141 code=0 clean 
codex/hist-bounds-2145@cb5700a1a files=316 code=1 clean physical/die_plan(1) 
codex/kv-pickup-2034@2fa2cc37f files=222 code=13 clean tools/qwen_layerbench(13) 
codex/pslice-look-0910@c79f3cf7f files=26 code=0 clean 
codex/s81-die-2032@70d4f439f files=180 code=12 CONFLICT physical/die_plan(10) tools/mem_compiler(1) tools/die_plan(1) 
codex/eco-postroute-lec-1102@77071ae92 files=89 code=26 clean tools/die_plan(21) tools/fleet(2) tools/autopilot(2) 
codex/qwen-headlease-candidate-2145@36c29aceb files=225 code=11 clean tools/qwen_layerbench(10) rtl/test(1) 
codex/head-wave-collect-1102@28e2e68a5 files=231 code=0 clean 
codex/geom-1101@a1699d08e files=260 code=0 clean 
codex/tt-locality-prep-1102@c75257ab3 files=213 code=19 clean tools/die_plan(19) 
codex/native-head-consumer-prep@f5cb65a89 files=154 code=37 clean tools/qwen_layerbench(28) rtl/test(9) 
codex/pg-filler-1102@20cf4becc files=27 code=7 clean tools/openroad_pg_birth(6) physical/common_flow(1) 
codex/hhp-clock-mesh-role-1102@62b7f134b files=110 code=14 clean tools/die_plan(7) physical/die_plan(7) 
codex/kv-pc-reload-checkpoint-0020@dc56d1591 files=143 code=2 clean tests/test_kv_core_pin_audit.py(1) physical/die_plan(1) 
codex/t51-role-banks-0940@18067ea26 files=8 code=2 clean tools/die_plan(2) 
codex/clock-obstacle-union-2208@c9cb77c98 files=148 code=13 CONFLICT tools/die_plan(13) 
codex/recip-place-pg-canary-prep-0810@1b0d54c45 files=19 code=0 clean 
```

## 5. Codex OWNER? questions since 11-01 20:34 (CODEX-LOG.md lines 9783-end)

Coverage legend: COVERED = a COORD/OWNER ruling exists (COORD-REVIEW-QUEUE 11-02 17:50-18:02); OPEN = no ruling found, owning lane rules it die-locally or posts an ASK.

| # | log line | question (short) | Codex options / default | ruling status |
|---|---|---|---|---|
| O1 | 9786 | HBM KIT-WAVE-16 q_su11/q_spu0 partition-type pilots before die clock PASS | allow scoped allowlist / default HOLD | COVERED: OWNER 17:57 (5): HBM unfrozen, die problems first, NO type pilots/volume |
| O2 | 9794 | HCOL shared-input repair: additive regional master, 1113 dup input pins (1216->2329), 0 FF/0 cycles | adopt after boundary/capacity checks | COVERED: COORD 17:50 (2) ADOPT -> DIE-HBM-58 |
| O3 | 9798 | Short-stage pool <=8 GB/2T excludes gen_lint (10 GB) | widen or keep | COVERED: COORD 17:50 (1) <=10 GB/2T; KW-FIX-1 READY 4484d5145 |
| O4 | 9802-03 | Qwen native HEAD/stage37 programme/loader/calendar event (X*RSTD*gain before HEAD) | adopt canonical scope? | COVERED: OWNER 17:57 (6) HELD, default-off, TOK-QW-3 |
| O5 | 9805 | HBM mu1: no real high-row producer bit for 16 SW/SE callers | which producer/source event; no zero-ext | COVERED in part: COORD 18:02 (b) four-stack (A); mu1 producer pricing -> TOK-HBM-1 (COORD 17:50 "HBM four-stack/mu1 TOK-HBM-1 to price") |
| O6 | 9809 | Coordinator host 'ubuntu' bounded heavy share | yes / default keep restriction | COVERED: OWNER 17:57 (7) no heavy on coordinator |
| O7 | 9818 | L2 publish as reconstructed-current-source kind, original_build_commit=UNKNOWN | reconstructed kind vs fabricate | COVERED: COORD 17:50 (3); SIGNOFF-SPRINT-21 wrote PROVENANCE 17:56 |
| O8 | 9835 | HCOL regional split cost clarification (+1113 parent FF/half-col, up to 142464) | qualify global delta | COVERED by O2 ruling + OWNER 17:55 (4) shared producers |
| O9 | 9839 | BF return-row namespace: global rank row_index vs phase-local + collector remap | A global / B phase-local; disabled 06ef2d7dd | OPEN -> TOK-DS-3 (die-local DS source choice) |
| O10 | 9845 | S81 L5 placed A/B: parent/child pin-contract reorder (vi_n north, rs_o south), keep 2-edge latency | authorize reorder / 3rd pass stage (+1 edge) | OPEN -> DIE-S81-48 (die-local; OWNER 12.21 tok loss OK) |
| O11 | 9849 | L2 retained M4/E clock pin vs centre-M5 rule: publish under legacy measured-clock contract, or rebuild | publish w/ disclosure / new build | COVERED: COORD 17:50 (3) + SS21 17:56 published with M4 + TT324.51/FF262.56 disclosure; parent real-view STA still required |
| O12 | 9861 | QC UCIe hard provider: model-only nface_g5_lclk; which real UCIe/clock service | none available | OPEN (no real provider exists; owner-level) -> DIE-QC-63 to keep MODEL_ONLY and post one plain OWNER line if it blocks QC die STA |
| O13 | 9869/9872 | G5 native HEAD stage37 static calendar / witness price (WTN PW439..444, ~300 FF, 0 boot words) | informational, default off | COVERED by O4 (stage37 HELD default-off) |
| O14 | 9891 | KV CTL ~9% fill at 371.52 sq: proceed under area ruling vs repack parent/core interface | (a) proceed under explicit area ruling / (b) repack | COVERED in part: standing OWNER fill-exception rule (fill <0.15 -> exception by default unless it blocks closure) => (a) proceed; DIE-KV-61 confirm |
| O15 | 9896 | QUERY head5 nested HCOL q565 input ABI event | approve q565 event / keep join held | COVERED: OWNER 17:55 (4) keep shared producers, no private captures; DIE-HBM-58 |
| O16 | 9905 | AHUB clock source: exact RECIP/ZH native checkpoints missing on all hosts; any backup? | none; UNEXPANDED_CHILD_ETM stays NOT RUN | OPEN (factual: no backup found) -> DIE-KV-61: rebuild children from source (RECIP/ZH FP+PLACE already done by Codex) |
| O17 | 9926 | QC L1 retained-route repair 32GB/4T (g0c-regress-1101@4d31e85cd) + R+L filler callback (pg-filler-1102@f36c72977) | authorize one each | OPEN -> DIE-QC-63 (route repair) + FLOW-22 (filler callback review); closure-first => default authorize |
| O18 | 9949/9955 | HHP selected KV clock cohort (tree_kv58 link_htree vs d25/m25 mesh) | resolve cohort | COVERED: COORD 17:50 (4) tree_kv58, fix plan_c metadata |
| O19 | 9961 | QUERY head5 private captures 35520 FF/definition (71040) pricing | private vs shared | COVERED: OWNER 17:55 (4) shared, no private captures |
| O20 | 9977 | S81 LLfu DRT-only observational zero-diode run, 8GB/2T, gen12_drt_only | authorize one run | OPEN -> DIE-S81-48 (die-local, closure-first: default authorize) |
| O21 | 9980 | HBM BFQG classifier: add obstacle-aware actual-route witness for channel_v 1.04 false forced cut | add witness / default HOLD | OPEN -> DIE-HBM-58 + GEOM-110 (no new restrictive gate; this relaxes a false fail with measured evidence) |
| O22 | 10000 | VN_b HW_STAGE0 no-CONST_ZERO SYNTH-only sizing add to wholeKV scope | authorize | OPEN -> DIE-S81-48 (SYNTH-only, default authorize) |
| O23 | 10012 | QC L7 one ordinary native DRT-only 32GB/4T from ed1fe2db checkpoint | authorize / default HOLD | OPEN -> DIE-QC-63 (closure-first: default authorize) |
| O24 | 10017 | QC retained slot-event CDC: (a) ready/hold with real feedback vs (b) pulse ports + qualified spacing + sticky overflow | (a)/(b); 594c0dca0 async FIFO W7/D4 | OPEN -> DIE-QC-63 (covered in spirit by OWNER 17:55 (2) "adopt QC GLUE/SC events gated on equivalence"; recommend (a)) |
| O25 | 10027 | HEAD SerDes sender FCLK/FSTART: A declared-root + measured delta vs B shared CTS leaf | A/B | COVERED: DIE-HEAD-54 17:51 (5) A, COORD 18:02 (c) concur |
| O26 | 10034 | S81 LLfd sole CTS callback canary 8GB/2T (codex-pg-birth-cts-0219/cts_pg0_0253) | authorize one | OPEN -> FLOW-22 (PG-birth CTS scope) + DIE-S81-48 |
| O27 | 10039 | Hroot: replace held 0415 lifecycle with strict packet codex-hroot-chunk-STRICT-PREP-0830 after PG 728a529a0 | replace / keep | OPEN -> DIE-KV-61 (superseded in part by OWNER KV.HROOT 17:57 pipeline-stage event) |
| O28 | 10043 | Native HEAD tail publisher: valid-row mask (~65 FF/tile) vs raw publisher + armed station | A/B | COVERED: OWNER 17:55 (3) A ~65 FF |
| O29 | 10048/10055 | HEAD WTX 14 unreset idle pad bits: N2_TAIL_PAD_ZERO vs wait for refinement policy; bit-exact preservation 69812606f first | test preservation first | COVERED: DIE-HEAD-54 17:51 (1), COORD 18:02 (c) |
| O30 | 10051 | HEAD tail ~5-FF transition-contract variant | propose only | COVERED: DIE-HEAD-54 17:51 (2) NOT adopted |
