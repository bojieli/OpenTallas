# OpenTallas release tree (pending only; coordinator update 2026-11-01 18:00 PST)

**Status 2026-11-06 14:39 PST:** count 182 (S81 53/58 + 9/205 types, HEAD 4/4 + 13/25, QC 24/26, KV 30/32 + 1/56 types, HBM 48/103); UP 2 from 180 at 13:35 (KV qkd_hr_core_peer, HBM q2_hard_v8g__reduce re-sign). Counted by hand on top (NEEDS_PARENT): HBM ot_hgi_gq_aq_tile -> 183. Signed but not in the count: S81 rom_q he half (hw half in ECO; plan split event pending), HBM type idx_tail_native vf56d1f7. Main de614b8eef7 (I213-I217, kit-wave crash hot-fix merged); ROOT-MERGE-45 has sysSD 77f12d1368, PART 38/41 being regenerated. New class: S81 kit rows 'other flow error' 18 -> 31 (bk_sel__t2 +30) -> KW-FIX-24. HBM 31 cores never built -> DIE-HBM-82 batch. GEOM 14:3x: S81 t51 W placed WARN (54k buffers vs 28k FF, long register rows; GRT ov 0), KV prompt 254.88 slot OK. Disks scratch2: epyc4 71 GB (99%), epyc2 57, intel2 93, epyc6 89, intel1 104, epyc5 141; PRUNE-1122 waits on KW-FIX-24 'kw-fix-4/kw11 free'.
Plans 11:36: count 152 flat (S81 50/58 + 4/205 types, HEAD 4/4 + 12/25, QC 16/19, KV 26/32, HBM 40/103). Merged I118-I126 since 10:40: QC coll_core fold + ring ff class (tag e-qc), KV PV taps (tag b-kv), HEAD l48ue (tag a-head), wave prune + resume fixes. 9 core gaps from CORE-FORMS-2 all owned. intel2 scratch2 142 after 49 GB move.

<!-- BREAKDOWN BEGIN -->
## FAILURES · unsigned cores and types by class (auto, 2026-11-06 14:39 PST)
- [ ] FAIL.S81.CORES 53/58 signed · open: running, no result 2 (dsdv_bksel_q, v41_rom_elem_q_qxpq_w10_gb) · flow/tool error 1 (dsdv_idx_tx_n32) · not tried 1 (dsdv_bk_g) · LEC 1 (dsdv_eng_rr_e)
- [ ] FAIL.S81.TYPES 9/205 signed · kit rows: running 97 · other flow error 31 (bk_sel__t2, +30) · congestion 27 (col_h10_r0_p4__t1, +26) · timing after route 11 (slice_station__t14, +10) · waits on child core 6 · hold after CTS 3 (iqf__t1, +2) · global_place error 2 (slice_station__t52, +1) · kit_rtl 2 (s81sl_leaf__t58, +1) · cancelled (superseded) 1 (col_h9_r2__t1__cl87f3ff59) · no host 1 (dsdv_slice_kv512_C__t1)
- [ ] FAIL.HEAD.CORES 4/4 signed · open: none
- [ ] FAIL.HEAD.TYPES 13/25 signed · kit rows: running 5 · cancelled (superseded) 4 (hd_ctl, +3) · hold after CTS 4 (hd_lep0N, +3) · other flow error 3 (hd_spn_eshim_rx, +2) · timing after route 1 (hd_spn_wshim_tx)
- [ ] FAIL.QC.CORES 24/26 signed · open: running, no result 2 (qfd_tile_nk_a0c, qfd_tile_nl_a0c)
- [ ] FAIL.QC.TYPES 0/119 signed · kit rows: waits on child core 38 · running 25 · hold after CTS 18 (coll_ftm, +17) · running (>150k advisory) 15 (sle_fe_v1__cl8210183c, +14) · other flow error 4 (sle_ctl__cl372cea1c, +3) · timing after route 2 (coll_ftn, +1) · congestion 2 (coll_ft__cl78c7b300, +1) · cancelled (superseded) 1 (sle_stm_v2__cl7b3062fa) · no host 1 (slw_stm_v1__cl05fc43f7__cl2086fa2c)
- [ ] FAIL.KV.CORES 30/32 signed · open: running, no result 1 (qkd_hr_ingest_eng) · LEC 1 (qkd_hr_core_prompt)
- [ ] FAIL.KV.TYPES 1/56 signed · kit rows: running 22 · waits on child core 10 · other flow error 8 (kv3_hg_v1, +7) · congestion 2 (kv3_io_cor, +1) · hold after CTS 2 (kv3_pv_v3n, +1) · running (>150k advisory) 1 (kv3_hub_Ei) · no host 1 (kv3_io_ft_v1)
- [ ] FAIL.HBM.CORES 48/103 signed · open: not tried 31 (hc_bank128_pair_core, hfd_coll_q3_body_ctl, hfd_coll_q3_edge_arg, +23) · running, no result 17 (hfd_coll_q2n2_vm_core, hfd_coll_q3_vm_core, hfd_hgi_vms_glue_nw_t, +14) · structural hold 2 (hgi_sfu_core_split3__ctl, svc_pc_ctrl_leaf_cfg_h9b) · flow/tool error 1 (idx_score_hcol_h0_rb) · LEC 1 (idx_rootctl_static_am) · timing after route 1 (hc_subtree32_core) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp) · clock window (resume) 1 (hgi_sm_xload_cl2_ctlx)
- [ ] FAIL.HBM.TYPES 0/81 signed · kit rows: waits on child core 60 · hold after CTS 4 (hnx_vms_bank_q0_faces__vecd4ae__v32e0dfcad68a, +3) · other flow error 3 (hc_bank128_pair_core__v7d149b37532c, +2) · timing after route 2 (hgi_coll_gq_land__v25778639ea1b, +1) · re-sign (flow tag) 1 (idx_tail_native__v9496b22d4b49) · signed (count pending) 1 (idx_tail_native__vf56d1f72f3f3) · congestion 1 (hnx_vms_bank_q0_faces__vecd4ae__v39c3624d7cc9)
<!-- BREAKDOWN END -->

## EDIT · rules
- PENDING items only, one short line each, edited in place. Remove an item when done (evidence goes in PATH-FREEZE.md / lane files).
- Line form: `- [ ] ID task · OWNER · STATUS · current fact → DEP.ID` ; "→ X" means this item waits on X (each → is a link).
- Gate ids per die are PFX.INFRA / PFX.GRT / PFX.CLK / PFX.BIND / PFX.STA.
- OWNER 12.18 (2026-10-29 05:44 PDT): full-gate census per die -> lanes/CLOSURE-LIST.tsv (fixed list); rule freeze (new checks only by owner); hourly burn-down open/closed/added; all 5 dies in parallel.
- OWNER 12.17 (2026-10-29 05:31 PDT): freeze plan on die GRT0+clock pass (fix-only after); one clock tool ot_clk.py for all dies; 2 parallel fix variants per failing gate; strict bind clean before GRT counts.
- DIE METHOD = METHODOLOGY s12 v5.1 (v5.0: early taps = macro insertion balancing, AOCV 0.21%/mm gates; v5.1: trims/useful skew/pads sparse <=~5% + CLOCK-RESIDUAL ledger after structural fix; 5%/15% cost = targets) (OWNER 10-26, frozen; change only on measured failure + owner decision): 12.7 MASTER PLAN FIRST per die (census -> corridors <=0.6 -> bays <=405 um every path/layer -> M7 entry pins -> worst-case PG, PG-shielded clock, islands clock/reset only, one core latency) + static plan gates incl. analytic predictor BEFORE any block build; kits carry a plan slice. 12.8 clock by construction: plan-defined centre clock entry per core, 250 ps TT, structured core trees; NO early taps / post-measurement trims / clock ECOs / mesh-node CPPR (plan-computed per-tap sizing OK). Freeze = GRT0 incl clock (>=50 it) + DIE STA with the real clock on related pairs (TT setup, FF hold; CPPR to last tree node); 80 ps skew = design target only. v4.6-4.9: MSCTS H-tree->ONE continuous mesh (signed mesh = CPPR point)->short local trees; clock OCV = depth/distance table (draft, owner review); droop shared (clock charged differential only); data hold buffers allowed. 12.9: one owner per die plan/clock (lanes/OWNERS-DIE.md); gate numbers via NUMBER-CHECK.
- Release gate = die STA on real views + token pass.
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS FROZEN BLOCKED NOT RUN.

## DIE s81 · S81 · rev plan_h2_2249 + RF1 · FROZEN (one-block fixes) · count 47/57 + 4/205 types at 06:05
- [ ] S81.PROUTE Station safe form (OWNER 11-02 pilot + 11-03 safe forms) · S81 / S81-PROUTE-2 (DIE-S81-65) · RUNNING · MAIN = FIXED-BAY: relay flop + negative-level lockup latch + repeater bays pre-placed <=405 um, local leaf per bay, per-hop delay/slew/hold computed before route; parent-route kit p7S_x11 (GEN_LINT + PREFLIGHT PASS) kept only as comparison; result applies to QC stations as one class
- [ ] S81.BIND Strict native bind · S81 / DIE-S81-65 · PASS · event2 completed 11:40:42; 398 partitions / 204 types / 873 crossings / 606281 bits, connectivity errors 0; this is not a routing pass
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kits sign; hold gate now >= 0 (OWNER 11-02) → S81.TILES
- [ ] S81.GRT Whole-data-die global routing · S81 / DIE-S81-65 · NOT RUN · no qualified current all-partition signal+clock GRT receipt → S81.TILES → S81.PARENT
- [ ] S81.STA Complete die TT setup / FF hold on real views · S81 / DIE-S81-65 · BLOCKED · retained partial run: TT +31.30, measured FF +10.75 on 65420 pairs; 747728 hold pairs unmeasured; current full-die propagated STA absent → S81.GRT → S81.TILES
- [ ] S81.TILES Required current child / partition views · S81 / KIT-WAVE · RUNNING · cap B route/finish/RCX DRC0 ANT0, 748 pins preserved, final signoff+ownEQ next; L2M repaired route clean, final gates pending; Xfin relief GRT still running after prior202overflow
- [ ] S81.PARENT Production parent composition · S81 · BLOCKED · QBS SYNTH reached but nine exact selected hard-child implementation/model joins missing; PINCOPY histogram parent proof+GPL running, child signed/EQ1866 does not qualify parent → S81.TILES
- [ ] S81.T41 Forwarded data/K timing witness · S81 / GEOM · WAITS · corrected A/B only placed; default-OFF observer ready4b96673bc; one baseline-A CTS+witness needs review, old GRT4750 remains FAIL → INFRA.REVIEW
- [ ] S81.RESET SerDes warm-reset sequencer implementation · S81+HEAD / DIE-S81-65 + DIE-HEAD-71 · RUNNING · OWNER 11-02 17:55 closed the choice: local sequencer holds reset >=64 rck edges after PMA clock restart, no running-clock promise; shared module adoption on S81 in progress (helper reset) → READY

## DIE s81_head · HEAD · rev l48rf + l48rc, one plan l48ua merged I35 (all 25 types gen rc 0) · count 4/4 + 12/25 types at 06:05
- [ ] HEAD.BIND Current parent source / child-model composition · HEAD / DIE-HEAD-71 · BLOCKED · exact current source+views must compose before full parent release → HEAD.TILES
- [ ] HEAD.CLK Current die clock qualification · HEAD / DIE-HEAD-71 · BLOCKED(kits) · clock proof l48w_sth GRT0/TT+252.75 stands (older pass counts); l48w_sth GRT0/TT+252.75/START0of1607; only2 real core views,0 kits plus declared budgets; 530106 hold pairs unmeasured, not current full-die timing → HEAD.TILES
- [ ] HEAD.GRT Current whole-die signal+clock global routing · HEAD / DIE-HEAD-71 · BLOCKED · retained infrastructure routing is not a complete current parent data-route receipt → HEAD.TILES → HEAD.BIND
- [ ] HEAD.STA Complete current parent TT/FF and seam timing · HEAD / DIE-HEAD-71 · BLOCKED · actual all-bit parent interface/hold qualification absent → HEAD.GRT → HEAD.TILES
- [ ] HEAD.SERDES kp4 e13a own routed equivalence · HEAD / SIGNOFF-SPRINT-19 · RUNNING · n-head SIGNED TT+2.48 FF+11.85 DRC0 ANT0 faceguardPASS; existing own routedLEC CPU-active, await actualEQ before count
- [ ] HEAD.TILES Current partition physical closure · HEAD / KIT-WAVE · RUNNING · STmD route DRC0/antenna0, finishRCX/signoff+EQ pending; original tile/spine/HOST repairs continue; current HOST timing/DRV/neck and meshFF-104.83 unresolved → HEAD.SERDES
- [ ] HEAD.HOSTLEC Current routed HOST qualification · HEAD · WAITS · retained component136216EQ complete; newer routedb2 is a different subject and still needs its own proof+physical closure → HEAD.TILES
- [ ] HEAD.SEAM Mesh sender/receiver timing contract · HEAD · BLOCKED · finite hold repair hits setup-versus-hold feasibility; any seam rebudget needs actual peer and parent TT/FF qualification, no constraint relaxation → HEAD.STA

## DIE qwen_compute · QC · rev plan_qc52 + CA+1 + y-shrink2 · count 14/19 at 06:05
- [ ] QC.BIND Strict native bind · QC / DIE-QC-81 · PASS · 119 types / 377 parts,0 errors; G0C completeness remains FAIL11
- [ ] QC.CLK Native die clock implementation · QC / DIE-QC-81 · BLOCKED · 51596 planned cells / 10929 taps sourcegeometryPASS; native prefix is unexecuted, no parent PG/GRT/RC/STA or START-freeze credit → QC.CLOCKPREFIX → QC.TILES
- [ ] QC.CLOCKPREFIX Bounded native clock import/access diagnostic · QC · WAITS · exact current homes/aliases reviewed; staged64GB8T geometry-only import, no legalization/GRT/STA; awaits root scoped release → INFRA.REVIEW
- [ ] QC.GRT Whole-die signal+clock global routing · QC / DIE-QC-81 · BLOCKED · no current whole-die GRT pass → QC.TILES → QC.GLUE → QC.CLK
- [ ] QC.STA Propagated whole-die TT setup / FF hold · QC / DIE-QC-81 · BLOCKED · no complete current parent STA; count-alignment or child timing is not die timing → QC.GRT → QC.TILES
- [ ] QC.TILES Qualified partitions and capacity · QC / KIT-WAVE · RUNNING · Q4 official177206EQ complete; all8SU pre-routeEQ complete; L1 finalGRT TT-14.64 FF-2.52, three-edit PLACE coupon pending; required unsigned views remain
- [ ] QC.SC SC source+clock-count event and first physical closure · QC / DIE-QC-81 · RUNNING · OWNER 11-02 ADOPTED (EQ/sim-gated; 8 SC types >400k cells need CORE-KS split); actual336662std / wholeEQ55664; sharing changes default-mode FF43058→42671, so not dormant; corrected572bit legal-trackGEN+LOOK passes, first PLACE awaits review; chain-end variants require separate handling → OWNER.SOURCE
- [ ] QC.RED RED source/parent event and clock implementation · QC · BLOCKED · actualPLACE225665std/34225FF/40.268%fill; same8269node sink rebind max15.77um is planning only; root/common-frame and parent+1 event unqualified → OWNER.SOURCE
- [ ] QC.STM Current native STM qualification · QC · RUNNING · corrected slw_v3 GEN17874contactsPASS, ordinarySYNTH→PLACE queued; two additional exact source/count matches224247/222702std, other distinct types still incomplete
- [ ] QC.GLUE Joint parent/interface geometry event · QC / DIE-QC-81 · RUNNING · OWNER 11-02 ADOPTED (EQ-gated; pipeline stages for 1838>1110 um reach); coordinate coupon legal but5306long reaches remain; fixedSTART1838um exceeds1110um reach budget; compact proposal leaves1088.64um parent gap and missing west peers → OWNER.SOURCE
- [ ] QC.NL Corrected clock-inclusive GRT probe · QC · WAITS · prior attempt failed MM context before FF; same-byte4_cts alias+configuredmargin10 fixture passes, one bounded retry awaits root → INFRA.REVIEW

## DIE qwen_kvsys · KV · rev plan_c (32) + RF-KV1, event on main · count 24/32 at 06:05
- [ ] KV.BIND Current strict native bind · KV / DIE-KV-79 · PASS · source connectivity passes; no physical die credit
- [ ] KV.CLK Complete current real-view clock timing · KV / DIE-KV-79 · BLOCKED(kits) · clock proof stands (older pass counts): mix TT+595.71/CA0of3595 has7coreviews,0kits plus budgets; FF37674pairs NULL/unmeasured → KV.TILES
- [ ] KV.GRT Current whole-die global routing · KV / DIE-KV-79 · NOT RUN · latest parent macro-fit vehicle explicitly dieGRT/route NOTRUN; reported zero-overflow successes are partition/core probes → KV.TILES → KV.HROOT → KV.HG
- [ ] KV.STA Current whole-die propagated TT/FF · KV / DIE-KV-79 · BLOCKED · no complete routed current-die timing receipt → KV.GRT → KV.CLK
- [ ] KV.TILES Required hard-child and partition closure · KV / KIT-WAVE · RUNNING · EX70 SIGNED+own20490EQ publishedHG-only; PCfMX GRT0 now timing/repair, AHUB/PV/PHY and HR source-follow work remain
- [ ] KV.HG HG native9-child qualification and parent geometry · KV · RUNNING · parentSYNTH189754std+30macros; q1 currentgold→actualfinal proof admitted normally; six current views need reconstruction,1057bit corridor still needs placed endpoints/shared-demand reservations → KV.TILES
- [ ] KV.HROOT Parent geometry/reset source event · KV / DIE-KV-79 · RUNNING · OWNER 11-02 ADOPTED (EQ-gated; retiming/pipeline for 2192>1920 um); fixed separation2192.120um exceeds1920um bound by272.120; reset repoint has real observer counterexample; local placement cannot close → OWNER.SOURCE
- [ ] KV.FORMAL CTL/HHP/RX native closure · KV · RUNNING · CTL123diff, HHP5persistent enabled/unreset-state failures; RX native+emitted17769EQ, mapped gate pending; complete new proof-helper bundle waits publication → INFRA.MERGE
- [ ] KV.RECIP Compact RECIP and ZH physical qualification · KV · WAITS · RECIP GRT TT+161.66 FF+9.67 but actualfill15.27/empty68.78 FAIL; ZH actualfill45.589 and independentLOOK supports one PLACE diagnostic → INFRA.REVIEW
- [ ] KV.FN Production token execution · KV / TOK · RUNNING · sole correctGEN1 probe fault0, nofirstcal; observed~2.3cycles/s implies~35h for290307-cycle window at that rate, not measured token throughput → TOK.QW

## DIE hbm · HBM · rev d44v_por (parts 1-7) · count 37/95 at 06:05
- [ ] HBM.BIND Qualified current native production composition · HBM / DIE-HBM-76 · BLOCKED · native source/pin/profile and clock/START joins incomplete; historical wrapped bindings do not qualify current production → HBM.CLK → HBM.TILES
- [ ] HBM.HUBMESH Hub mesh / production clock integration · HBM / DIE-HBM-76 · STRUCTURAL PASS, BLOCKED(kits) · hub mesh a3e6s, NE_v2, die TT +93.69, CA 773/773 (hold margin 0); next: plan event d44v (q3_edge single-column slot, pslice_c5 2.6-um macro channels, xload ctlx, hnx fused) -> kits -> real-view hold
- [ ] HBM.CLK Native clock/source/PG composition · HBM / DIE-HBM-76 · BLOCKED · 21 station types planned3077ports pass consumer/S0parity;283plannedhomes,260sourcehomes(16mismatch),23missing; active-role/native pin/net/START joins remain unqualified
- [ ] HBM.GRT Complete current die global routing · HBM / DIE-HBM-76 · BLOCKED · planned station/clock repairs and historical wrapped probes do not establish joint current signal+clock GRT → HBM.CLK → HBM.TILES
- [ ] HBM.STA Complete current die real-view TT/FF · HBM / DIE-HBM-76 · BLOCKED · actual native child models and propagated production clock/parent timing incomplete → HBM.GRT → HBM.TILES
- [ ] HBM.TILES Current native source / physical qualification · HBM / KIT-WAVE · RUNNING · native VMS11560EQ, BFQG8650EQ, Tnode4730EQ; historic wrapped shell signoffs cannot substitute current native views
- [ ] HBM.PSLICE Corrected reset source integration and physical plan · HBM / DIE-HBM-76 · WAITS · legacybridge4419751comparisonsPASS, native4EQ108839; +24resetFF/0missioncycles, ready96b0c0184; fresh physical locality/fill still open → INFRA.MERGE
- [ ] HBM.PSTORE Native placement closure · HBM / DIE-HBM-76 · RUNNING ·70580EQ;51guides bind; priorGPLdiverged, sole unchanged-sourcephi1.01cached retry active; actualfreefill4.534% remains explicit
- [ ] HBM.QUERY Current head5 native equivalence · HBM / DIE-HBM-76 · RUNNING · face1622PASS; fresh native4 fullproof31379EQ/0diff with171hints, wrong-polarity control running; source/caller/clock event still PREP, no physical release
- [ ] HBM.TNODE Compact native parent event · HBM / DIE-HBM-76 · WAITS · oldactualfill6.57/empty83.41FAIL; compact125.28×95.04 preserves1341pins and30worldclock/PG positions, parentDATAevent+GEN/LOOK required → OWNER.SOURCE
- [ ] HBM.OPSTORE Native frontend/source cut · HBM / HBM-CORES-KITS-40 · BLOCKED · escaped-identifier frontend failure diagnosed; no wrapped-view alias or physical credit

## TOKEN · Token-pass gate per design
- [ ] TOK.DS DeepSeek whole-die token execution · TOK / S81 · RUNNING · whole-die frontend builds active; nativeSRAM16checkpointwords bothbanks PASS and CAP-safe representative fieldPASS, production mission not qualified → TOK.PROGRAM → S81.STA → HEAD.STA
- [ ] TOK.QW Qwen QC+KV token execution · TOK / KV · RUNNING · actual512XAwords4users pass livecalendar/nativeSU; HEAD stage has zeroSUops and weights/programme not installed in native form; KV solebootprobe not whole-token pass → TOK.PROGRAM → QC.STA → KV.STA
- [ ] TOK.PROGRAM Native arithmetic / programme / leases · TOK · RUNNING · ROOT arithmetic64GB build active, monitorXA live replayPASS, DSglobaldates/leases and HEADprogramme integration open; component transport is not full mission
- [ ] TOK.HBM Production HBM token execution · TOK / HBM · BLOCKED · historical accepted~1677tok/s remains scoped; current SOURCE11 frontend64GB/J2 MEMCG-OOM, one96GB/J1 checkpoint-resume queued normally; S0/S3 producers/packing/alignedstaging and visibility still open → HBM.STA
- [ ] TOK.E2E End-to-end token pass · TOK · NOT RUN · requires actual complete numerical/programme execution and qualified die timing → TOK.DS → TOK.QW → TOK.HBM

## FLOW · Flow release + workflow (OWNER 12.27)
- [ ] FLOW.KITS Current type-kit closure · KITS_FLOW / KIT-WAVE · RUNNING · collect/relaunch shared postCTS helper failures with complete pinned bundles; 17:20 coordinator reported core_clock_band staging crash, deployment/recovery must be collected before credit
- [ ] FLOW.CTS Retained CTS runtime portability · KITS_FLOW / S81 · WAITS · firstR1 failed beforeCAD on shallowcore_flow import; narrowfixf34267628 has42tests+actualcontainerpre-make smokePASS; sole dispatcher retry after review, R2separateheld → INFRA.REVIEW
- [ ] FLOW.COUNT Exact SIGNED+ownEQ / current-model counts · SIGNOFF-SPRINT · RUNNING · prior reported count50 differs from generated cache; neither is a fresh recount; e13a timingSIGNED waits ownEQ; EX70 HG-only child closure does not release parent

## INFRA · Merge, hosts, disks
- [ ] INFRA.MERGE Publish clean gated source/tool trains · ROOT-MERGE-24 · RUNNING · main 48c37eca7d3 (F5 QC red/HBM POR/TOK-QW-4/KV/S81 lnland/TOK-DS-4, F6 HEAD headgate, F7 TOK-HBM d44u); next: kw-fix-3-s81pf 4a2dae0f548, kw-fix-2 d483825fd6e (class R), die-kv-62-stations 7bbad22d032; FLOW-24 candidate RSZ-3006/RSZ-0074 286030c4f4
- [ ] INFRA.REVIEW Release concrete reviewed next steps · ROOT · RUNNING · retainedCTSfix/retry, QCnativeclockprefix, T41witness, NLcorrectedprobe, ZHPLACE and compactTnodeGEN; actualLOOK/source/reset/count scope before physical dispatch
- [ ] INFRA.DISK Scratch headroom · PRUNE-1103A · RUNNING · 04:3x free: intel2 251 GB (93%, was 63 GB 04:0x; released kit attempts + canary sources, Codex dirs MOVED to epyc2 root), intel1 207 GB (95%), epyc2 scratch2 324 GB; epyc2 root 1.3 TB (keep >=500); target >=300 each
- [ ] INFRA.LOAD Queue/build turnaround · KITS_FLOW / TOK · RUNNING · onlyepyc2/intel1/intel2 active; conserve progressing jobs, no duplicate proof/build; whole-hierarchy OOM and serial simulation are real schedule risks

## OWNER · Explicit contract decisions
- [x] OWNER.RESET Resolve soft SerDes reset authority · OWNER · DONE · OWNER 11-02: local >=64-edge reset sequencer; running-clock guarantee or priced safe local sequencer; no blanket reset extension; plain question logged, other work continues
- [x] OWNER.SOURCE Price coupled source/clock/count/parent changes · OWNER / ROOT · DONE · OWNER 11-02: SC/RED/GLUE/HROOT + compact native events adopted as explicit EQ-gated plan events; HBM unfrozen; Qwen stage37 adopted; SC default-mode sink change, RED parent event, GLUE/Hroot repack and compact native events require explicit adoption; no silent plan activation

## WAITS · who
### Waiting on the owner
- OWNER.RESET: soft SerDes stopped-PMA warm-reset guarantee or priced safe sequencer; no blanket4→64 reset assumption. Plain questions in CODEX-LOG.md, work continues.
- OWNER.SOURCE: explicit source/clock/count/parent events for SC, RED, GLUE, Hroot and compact native proposals; no silent canonical activation. Plain questions in CODEX-LOG.md, work continues.
### Waiting on COORD / ROOT-MERGE
- INFRA.MERGE and INFRA.REVIEW above are active queues; ready packages and diagnostics are not yet all published/released.
