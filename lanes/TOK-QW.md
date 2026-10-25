# TOK-QW (lane file)
Branch claude/tok-qw-1024 (worktree localhost:~/wt/tok-qw, base main 8a5d1f3dab). Hosts: intel1 (64 thr share) + ot-run.
Scope: Qwen ROM token-pass gate: compute-die layer runs (stg/head/attnret), compute<->KV D2D co-sim (TOK.QW.XDIE), composed 1u/4u.
Not mine: xt1/tp8/xdie-link/ovl4u (QC-TOK), KV-die token tests (KV-TOK).

## Current step
18:50 RESUMED (2nd limit). s8 bound-row compile intel2 35/36 C++ units; last (Vtb_vm_classes_8) running 6.5 h. Then s8cal2 slice/vec cal -> stage_stg_die.sh.
RESUMED 12:12 PDT (after 08:50-12:04 limit). Adopted from Codex: nothing live for TOK-QW except my own s8exp compile
(intel1 s8exp/die/build/obj_n12, g++ still compiling, left alone). codex/tok-qw-1024 @0a55cb9ec4 = parked F5/F7 bench
corrections already isolated on main (b1e16de8f0 F5 p192 name, 60c21cd01d F6 OBS1_COMPAT rx, 83e1cfdf48 F7 ROM pair) -> no merge
needed; xdie_bound F5/F6/F7 findings now have main fixes (opt-in; bound top still needs OBS1_COMPAT=1 adoption).
- xhead: 1st calibrate FAIL-no-edge (go_lag -2..6 all PASS, xpf edge 4). Relaunched 12:13 stage_xhead.sh --reuse
  (cached obj_xh, OT_XH_GO_MIN=-8; 10-23 edge was -3) -> per-consumer sweep -> 4 cases + 10 mutants. RUNNING.
- attnret: stage_attnret.sh on stg rel/pos obj_n12 + vec_ages, RUNNING 12:14.
- NOTE: intel1 ~/ot-scratch = /srv/opentallas-scratch is on intel1's ROOT fs (109 GB of mine there). New jobs go to
  /srv/opentallas-scratch2/claude/tok-qw; will move r1024 when s8exp/xhead finish.
06:58 PDT recovered old-fleet inputs before the 07:03 wipe -> intel1:~/ot-scratch/tok-qw/recovered (66 GB):
  fx_in (TP4 P8191 36-layer ISA gold + img_p1 + oracle.json, 32 GB), tokd-qw-main-1023 (head fx, link fx, xt1 in),
  tokqwm-1023 (10-23 record run), tokqw4-1022/stg3/fx, tokfunc-qw-1021 (non-build), codex qw-head-main-a970-1023,
  qw-r56-head-selected-1023, codex-kvchain-2140. NOT found: kv_pkt r17 explicit packet (lived on ep5/ep9).

## State found (task 1)
- stg4 is DONE (10-21 19:55, PASS 527/527, ISA 1,032,336/1,032,336, cal gate + VM ages qualified). The stg3 "normalized FAIL"
  = original pos MAT calibration without XC framer pre-arms + no VM-write probe (ages UNKNOWN); fixed by bench-only patches
  stg_cal_prearm.patch + stg_vm_probe.patch (stage_stg.sh). Release config is SU_LT=0 (stg5lt0).
- Latest record TOKe-QWM 10-23 (main 92c2417f6, results/rtl/tokqwm_1023): 8/9 PASS, head FAIL (lpf SEGCAL lockstep
  3317/27981, h16y leaf absent on main); compose 1u 269,452 cyc = 4,455.3 tok/s, 4u 11,811.3, price HELD (head FAIL, tp8 diag,
  gaps IMAGE CAPACITY / TILE DELIVERY / RoPE ROW producer->consumer).
## Runs (RUNROOT intel1:~/ot-scratch/tok-qw/r1024, assembly = git archive main 8a5d1f3dab; logs localhost:~/wt/tok-qw-logs)
- stg   : ot-run intel1 --mem 240, stage_stg.sh --su-lt 0 --fx recovered tokqw4 stg3/fx (36 layers) -- RUNNING since 07:01
- head  : stage_head.sh --leaf (die-selected leaf h16za native32_1r) -- DONE 07:05 PASS
- xhead : stage_xhead.sh (new) calibrate + per-consumer sweep + 4 cases + 10 mutants -- RUNNING
- s8exp : tb_qfd_dv2 FACE 3 = BOUND die slice row (s8 flat / ce_w5 / ce_l9h / ce_e5 per position) lint/build -- RUNNING
- xdie_bound: sub-lane (fork), see its section
## Results
- 14:3x MERGED main 40e086ead0 + d7bf8a8ba0 (record above). intel1 s8exp duplicate compile cancelled (own job; intel2 copy
  finished 29/32 units in 2 h at -j24). r1024/recovered/xdie_bound moved off intel1 root fs -> /srv/opentallas-scratch2/claude/tok-qw
  (symlinks left). Next: s8cal2 slice/vec cal -> stage_stg_die.sh (259 pos cases on the bound row; expected = pos verdicts).
- 13:5x RECORD (branch 6262d005ea, results/rtl/tokqw_1024): xhead PASS 4/4 consumers + 10/10 mutants (calibrate go_lag -3 /
  xpf 4 with OT_XH_GO_MIN -8; consumer ages qkv -5/4 o -1/4 down -2/4); attnret PASS 98 == 98, ddwin/ddbase FAIL.
  compose (stg/head/attnret/xhead mine + QC-TOK tp8/xdie/ovl4u 3e05af806 + carried xt1/ctx4u/kv/chain): all 9 + 2 optional
  PASS, 1u 271,106 cyc = 4,428.1 tok/s, 4u 11,844.1; +1,620 cyc vs 10-23 = QC xdie on regen D2D constants (roundtrip 1887).
  PRICE HELD: IMAGE CAPACITY, TILE DELIVERY, RoPE ROW producer->consumer. Bound s8 row NOT RUN (compile on intel2
  /srv/opentallas-scratch2/claude/tok-qw/s8exp, s8cal2.sh, -j24, started 12:20).
- stg PASS on main 8a5d1f3da (slice2 chain, SU_LT 0, RUNROOT r1024/stg): 527/527 cases expected outcomes met, delivery
  timing qualified, 0 unknown; fixtures+builds 4119 s. Source assembly only (predecessor slice, not bound s8).
- head PASS (RTL-functional, die-selected leaf, main 8a5d1f3da): img0 123/123, imgh 131/131, bmut3 FAIL as required;
  LM-head stage start->END 3,135 = compiled 3,135 (plan price 3,101, +34). 10-23 FAIL cause: the behavioural h16y family is
  not on main + generic LP lockstep (abandoned LP, not the die parent). stage_head.sh --leaf added.
- FINDING: bound_r8 substitutes qfd_dv_slice2 by qfd_dv_s8_flat (+ chain-end variants) = SU_LT 1 / HD_W130 1 / MU_NU 4 /
  ARF1 RP1 + HARD leaf registers + treq lane. The stg stage (tb_qfd_dv2, qfd_dv_slice2 SU_LT 0) is the predecessor slice,
  not the bound slice -> building a FACE 3 tb on the bound s8 row.
- kv/chain: KV r17 vehicle readset 53/53 non-bench files byte-identical 92c2417f6 -> main (record.sv identical too); the
  10-23 r17 child archives (explicit packet) were lost with ep5/ep9 -> carried, not re-run.
## OWNER?
- Bound top adoption of OBS1_COMPAT=1 on the KV status RX (F6 fix on main 60c21cd01d is opt-in, default 0) and the regenerated
  F7 ROM pair (83e1cfdf48) as the release images: needed before a bound compute<->KV token run can PASS by default.
- F1: compute glue d2d_rom TXDP params still unbound in bound_r8 (trap) -- bind D2D_TXDP_C/K from regen constants.
- KV r17 explicit-packet child archives lost with ep5/ep9: approve regenerating the ROOT-approved sha table (b0cc8cdca) or
  keep carrying the 10-23 kv/chain verdicts (readset 53/53 unchanged).

## xdie_bound (sub-lane)
2026-10-24 07:30 PDT TOK-QW/xdie_bound: compute->KV D2D co-sim on BOUND link ends, branch claude/tok-qw-xdie-1024 @2dca1cc835 (not merged).
- Run intel1 ~/ot-scratch/tok-qw/xdie_bound/run2 (ot-run unit oth-ubuntu-194042-1792851975, done 07:29); results
  results/rtl/tok_qw_xdie_bound_1024/README.md; tools tools/qwen_tokfunc/xdie_bound/run_all.sh. 23/23 configs as expected.
- Literal carve: KV bound_pv sys_c elaborates; compute bound_r8 glue does NOT (F1 d2d_rom TXDP trap, F5 missing p192 macro).
- Co-sim (bound master modules + bound params + seam 2,2,2,3,2,2/34,34,32,32,32,31,31, TXDP C 0a010308 / K 03030443):
  bound compute master x bound KV master FAIL = F6: compute obs1 STATUS v1 extension rejected by KV legacy status RX
  (ot_qwen_d2d_status_rx_sf); with the extension masked (diagnostic) PASS 35 layers bit-exact; source compute master PASS.
  C2K cmd 55, K2C r31 53, roundtrip cmd->r31 1887, kv_service 1779, exposed d2d 108/layer, status 49, period 7056.
  Mutants caught: TXDP_K 66/68, TXDP_C 9, seam KS_RXV/SK_TXP/CS_TXS +1, result bit, status done, PHY bit, run late.
- Audit: F7 both dies' compiled-in calendar images stale vs regen (KV dcal mu image period 249,600; compute ovl rope
  293,376; regen 258,048) and mutually inconsistent. Owner action: bind TXDP on d2d_rom, KV obs1 status RX (or drop the
  extension), regenerate both images, fix p192 macro name.

## CODEX notes
- Collected completed source stg result: PASS 527/527, ISA 1,032,336/1,032,336, delivery_timing_qualified=true. Head PASS 123/123 + 131/131, bmut3 caught, control span 3135 cycles (+34 vs price). Bound s8exp lint blocked by duplicate SRAM definitions (sram_models_nofatal.sv vs another supplied definition); next remove duplicate harness inventory and continue bound vehicle. Source result does not establish bound-s8 pass. XDIE F6 status-v1 rejection and F7 stale calendar require fixes.

- CORRECTION to initial CODEX provisional finding: s8exp duplicate SRAM messages are MODDUP warnings, no %Error. s8exp/die/build calibration is still building (make/verilator live), not failed; do not restart.

- CODEX took over receiver F6 on codex/tok-qw-1024 and isolated integration codex/qwen-status-integration-1024. MERGED main60c21cd01d (d6724513c9): OBS1_COMPAT default0 propagated through KV wrappers, existing v1 validator accepts valid extension with reserved[303:156] stillzero. Microgate530 checks PASS(default legacy lockstep400cycles,16validv1 cases,8malformed caught). Bound-master exchange T256/T8192 each35layers exact, every landing on compiled edge; RESULT/STATUS mutants caught. Roundtrip1887cyc,KVservice1779,period7056,0 addedcycles. Actual boundtop still needs optin after physical timing; source support is ready. F1/F5/F7 still separate.

## PARKED 2026-10-24 18:59 PDT
- Branch claude/tok-qw-1024 @5b89da34d8 (pushed, clean). Merged to main: 40e086ead0 + d7bf8a8ba0 (record results/rtl/tokqw_1024).
  5b89da34d8 (tools/qwen_tokfunc/stage_stg_die.sh) NOT yet merged.
- Results (main 8a5d1f3dab assembly, readset == current main): stg PASS 527/527; head PASS 123/123 + 131/131, bmut3 caught;
  attnret PASS 98 == 98 (ddwin/ddbase caught); xhead PASS 4/4 + 10/10 mutants (go_lag -3 / xpf 4 after widening OT_XH_GO_MIN
  to -8). Compose with QC-TOK tp8/xdie/ovl4u + carried xt1/ctx4u/kv/chain: 1u 271,106 cyc = 4,428.1 tok/s, 4u 11,844.1.
  PRICE HELD: IMAGE CAPACITY, TILE DELIVERY, RoPE ROW producer->consumer. xdie_bound F5/F6/F7 have opt-in fixes on main (Codex).
- Failures / not run: stg on the BOUND s8 slice row NOT RUN (vehicle still compiling).
- Live job (mine): intel2 ot-run unit oth-ubuntu-2336359-1792869646 (local ot-run client pid 2606671, log
  localhost:~/wt/tok-qw-logs/s8cal2.otrun.log), script /srv/opentallas-scratch2/claude/tok-qw/s8exp/s8cal2.sh: make -j24 of
  tb_qfd_dv2 FACE 3 obj_n12 (35/36 units done, last Vtb_vm_classes_8.cpp ~6.6 h in), then slice + vec calibrate
  (die/build/slice_calibrate.out, calibrate.out, timing.txt). Leave it running.
- Next step: when s8cal2 shows rc=0 on both calibrates, run on intel2:
  bash /srv/opentallas-scratch2/claude/tok-qw/s8exp/stage_stg_die.sh /srv/opentallas-scratch2/claude/tok-qw/s8exp
  /srv/opentallas-scratch2/claude/tok-qw/s8exp/stg_result.json /srv/opentallas-scratch2/claude/tok-qw/s8exp/pos_runlist.txt --par 24
  (via ot-run; fixtures already in s8exp/stgdie/fx) -> stgdie/result.json; commit to results/rtl/tokqw_1024/stages/stg_die,
  merge, recompose. If calibration fails: record it as a FAIL finding (bound s8 row vs slice2 ages).
- RUNROOTs: intel1 /srv/opentallas-scratch2/claude/tok-qw/{r1024,recovered,xdie_bound} (moved off root fs; symlinks in ~/ot-scratch/tok-qw).
- OWNER?: see OWNER? section (OBS1_COMPAT=1 + F7 ROM pair adoption on bound top; F1 TXDP bind; KV r17 archive regeneration).
- UPDATE 19:1x (after park, no new job started): s8cal2 finished. The bound-row Vtb BUILT (intel2 s8exp/die/build/obj_n12/Vtb,
  make 24,664 s), but slice + vec calibrate rc=1 before simulating: "S8DIE: missing physical/asap7_memory_macros/
  ot_rom_4096x266_m8/ot_rom_4096x266_m8.v". The intel2 tree copy has physical/ as symlinks into intel1 paths (cp -as).
  Fix on resume: copy physical/asap7_memory_macros* for real into s8exp/tree (from a main checkout), rerun only the two
  calibrate commands from s8cal2.sh (the binary is reused because it already exists), then stage_stg_die.sh. This is a vehicle setup error, not an RTL FAIL.

## TOK-QK (steward) -- RESUMED 2026-10-24 19:29 PDT
- 2026-10-24 19:29 PDT TOK-QK: s8exp tree on intel2 had 581 symlinks into intel1 paths -> replaced by real files from main 8a5d1f3dab
  (git show). Relaunched calibrates (binary reused) + stage_stg_die.sh chained: s8cal3.sh, ot-run unit oth-ubuntu-1531267-1792895121
  on intel2 (client epyc1 ~/wt/tok-qw-logs/s8cal3.otrun.log). Next: collect stgdie/result.json, commit, recompose.
- 2026-10-24 20:49 PDT TOK-QK: stg_die on the BOUND s8 row = FAIL 0/259 run (259 unknown incl. rope_late mutant) -- RTL DEFECT S8-SU-PROG-ALIGN
  (owner lane QC): qfd_dv_s8_suvm_rp1 starts the closed SU (qfd_dv_s5_su8_rst3) and requests the program word on the same edge;
  SU latches the word 5 edges after the command but it arrives 8 edges after (vm8q_rp1 -> qfd_dv_s8x_prog) -> SU latches zero rows,
  stays busy forever, no fault -> no PSUM ever leaves; all 12 slices of bound_r8 (qfd_qc_sl{w,e}_su_c* u_u_suvm). Bench matches
  the bound contract (no bench changes). What-if (+3 edge SU start, NOT of record) on 2-slice vehicle: 3 rows, psums tags 1/13/25
  bit-exact; ssq_psum_out [171,187,203] (+88 vs slice2 SU_LT0, +67 vs SU_LT1; indicative). Evidence claude/tok-qw-1024 @81640ddb6c
  results/rtl/tokqw_1024/stages/stg_die/. Compose price stays HELD (source slice2 527/527 remains compose input).
  Live (diagnostic, not of record): intel2 ot-heavy oth-ubuntu-977696-1792899729 12-slice what-if (start delay +3) -> s8exp_wf3/stgdie.
## REQUEST from TOK-QK to lane QC
- QC-R4 (S8-SU-PROG-ALIGN): retime inside qfd_dv_s8_suvm_rp1 (SU start +3 edges or program-read path -3) and re-close the leaf;
  then I rebuild the s8exp vehicle and run stg_die of record.

## CODEX notes 2026-10-24 21:08 PDT
- CODEX took over: bound-s8 SU program alignment and exact gate on codex/s8-align-1024 (child s8_align). Source stages remain PASS; bound s8 stg_die FAIL 0/259 (259 unknown), SU consumes program 3 edges early. Existing wf3 diagnostic preserved, candidate retiming now owned. Next: exact miter+mutant, rebuild bound row, stage verdict then recompose.
- 2026-10-24 21:14 PDT TOK-QK: S8-SU-PROG-ALIGN fix sub-agent (claude/tok-qk-s8a-1024, takes over Codex codex/s8-align-1024; QC owns merge/re-close).
- 2026-10-24 23:01 PDT TOK-QK: S8-SU-PROG-ALIGN FIX on claude/tok-qk-s8a-1024 @445b1057e (RTL dd2d80455, rtl/qwen_dv/s5/s8/qfd_dv_s8_suvm_rp1.sv): SU start
  (su_cmd[9]) through 3 control flops (wf_st) so the closed SU latches the program word on its arrival edge; closed leaf
  qfd_dv_s5_su8_rst3 + read path untouched; SU command latency +3 edges (absorbed by calibrated SU ages). Proof: 2-slice vehicle fix
  PASS (psums tags 1/13/25 bit-exact at 1741/1757/1773), unfixed FAIL; random initial state 3/3 vs 3/3; fixed RTL == wf3 what-if
  (4,886 generated C++ identical) -> the running wf3 12-slice build IS the fixed-RTL build of record.
  Live: intel2 ot-heavy oth-ubuntu-977696-1792899729 (s8exp/dbg/s8wf3_chain.sh), C++ 1,879/~4,880 at 22:53 (~3 h) -> calibrates ->
  stage_stg_die.sh -> s8exp_wf3/stgdie/result.json + die/build/{slice,vec}_ages.json. Next: collect, commit as record, recompose.
  QC must merge + re-close qfd_qc_slw_su_c{,_v1,_v2}, qfd_qc_sle_su_c{,_v1}; regen physical/die_plan/qwen_compute/inputs/su_directed.json
  (pins old suvm_rp1 sha 067bba95).
- 2026-10-25 00:00 PDT QC -> TOK-QK: qwen_compute batched re-plan (claude/qc-meth-1024@a4ab2ba7fc) adds cycles on 792/2207 lanes (worst +15 on the
  CB rsf return lanes, +5 on all 96 CB a00/b00 ring lanes, +8 sl fw->ctl_p2, serdes +8/+9); per-lane old/new/delta:
  epyc1:/srv/opentallas-scratch2/claude/qc/meth_lat_delta.json. Constants follow from regen_constants on the new bind (in progress).
- 2026-10-25 00:26 PDT TOK-QK: wf3 (fixed-RTL) slice cal: ssq_psum_out [171,187,203] (slice2 SU_LT0 [83,99,115]); FAIL measured scalar hop 4 != compiler SC_HOP 2 -> sub-agent S8B (bound-contract hop vs defect; then vec/MAT cal + stg_die + recompose) on claude/tok-qk-s8a-1024.

## CODEX notes 2026-10-25 02:44 PDT
CODEX took over: fixed-s8 stage failure diagnosis on codex/qc-tokens-1025. Existing intel2 s8exp_wf3 stgdie remains LIVE, preserve. Slice/vec/MAT calibration PASS on 8b3d9f511 (scalar hop4, x-hop4 priced), but full-stage data gates FAIL: QKV385/769 with24/48VM writes; GU3073/3073; OD REFUSED STN window1320<1323; residual3/28, QK5/7, silu1/2. Diagnosed MAT topology mismatch: west even0/2/4 ce_* nb0 have no L9 input but compiler assigned them as finishing receivers (east6/8/10 works); own codex/s8-mat-1025 candidate uses west odd1/3/5, sender=receiver^1. Vector diagnosis underway: L0 residual expected sum34.537, delivered root scalar slots ~7, X readback stays original on slice0, consistent with missed T landing or scale data. Own readback-T simulation via ot-run intel2:/srv/opentallas-scratch2/claude/codex-qc-tokens/probe_t unit oth-ubuntu-3764919-1792921297. No RTL change or new PASS claim.

## CODEX notes 2026-10-25 02:47 PDT — MAT topology
CODEX took over bound-S8 MAT failures on codex/s8-mat-1025. Diagnosed L9 west-half topology mismatch: compiler finishes at slices 0/2/4 but those bound ce_w5/ce_l9h stations have no neighbour input; actual receivers are 1/3/5 (east stays 6/8/10). Candidate maps ownership accordingly, pairs sender with receiver via s^1, pre-arms STN before near producer words and uses measured far-to-AR latency for the inter-round guard. Own isolated jobs intel2:/srv/opentallas-scratch2/claude/codex-s8-mat-1025/{qkv_v3,gu_v3,od_v3}, compiled fixed-RTL binary reused. QKV first72/72 and GU first280/280 observed readback words exact vs ISA gold; final status and mutants pending, no PASS claimed. Inherited stage and paused trees preserved.

CODEX 2026-10-25 02:57 PDT MAT: OD fixed PASS 515/515 (both framed 256-word AR messages, zero collisions, strict status clean), span1555 cycles. Bound STN lead20 precedes near input/cfg fanout; inter-round guard uses measured far-to-AR minus the two outward registers (ctl own_ch + fdn ch_dn_o). QKV topology candidate at lead17 gives769/769 exact and48/48 VMwrites but FAIL station status; lead20 successor running. Fixed additional source defects: bound qkv_roles and calibration probe (slice1 replaces sender2), LM only clears/emits actual receivers (root0 has no local candidate); one-round six-receiver LM + count5 mutant jobs started on the same binary under lm_min/lm_min_mut. No RTL edits or additional hardware cycles.

## CODEX notes 2026-10-25 03:00 PDT
CODEX took over operand-age RTL repair on codex/s8-crom-align-1025@c1c42f554 (pushed; code3bcf717e8). Diagnosed CROM3issue edges late vsVM: all104 remaining L0residual outputs exactly match coefficienti-24, first24keepX; independentTreadback128/128exact. Optin OT_S8_CROM_ALIGN holdsVM3/BTAB1 and shifts head metadata3, preservingCROMphysicalrelays; defaults unchanged. Smallesthead miter2272cycles/288outputs PASS at+3edges, wrongVMdepthmutant FAIL288, dynamicweightcoverage PASS. Price+3edges/SUop in results/uarch/qwen_s8_memory_align_1025.json; needs fresh boundrowages/recomposition and physicalreclose. Separately own codex/s8-stream-1025 fixes Sched.keys occupancy2->ST_HOP4; clean+xslotSiLU runs live intel2codex-qc-tokens/stream. MATchild codex/s8-mat-1025 corrects westL9receivers1/3/5, prearm20 and localresultguard; QKV769/769/48VMwrites PASS, OD515/515 PASS strictstatusclean; GU/mutants pending.

CODEX 2026-10-25 03:07 PDT MAT: all three production-K cuts now PASS with strict status: QKV769/769 and48/48 writes (span445); GU3073/3073 and192/192 writes (span437); OD515/515 (span1555),0 collisions. Drop-last-K mutant caught1/769; minimum one-round LM26/26 PASS, AMNB5 mutant13/26 FAIL as required. Code codex/s8-mat-1025@9737553fe pushed; evidence follow-up collecting GU. All own MAT jobs terminal, none left running. No RTL change or hardware cycles added; STN commands14 edges earlier, source2slice rates remain held. Next: analytical price of CROM+3/SUop plus bound SC4/ST4/L9 ownership, no wide sims.
2026-10-25 03:16 PDT INFRA -> TOK-QW: epyc1 root disk (owner: no work on root): your LIVE item(s) still on the ROOT md0: ~/wt/tok-qw-logs. When the job ends, move it to the same path under /srv/opentallas-scratch2 (bash /srv/opentallas-scratch2/claude/infra-pass4/move_one.sh <path> -- copies, checks liveness, git worktree repair, symlink back) and create new run dirs/worktrees only under /srv/opentallas-scratch2/claude/.

CODEX 2026-10-25 03:15 PDT MODEL (predicted only): historical source271106cyc/4428.1tok/s reproduced; bound SC4/ST4/L9/occupancy286726cyc/4186.9; plus CROM+3/SUop288025cyc/4168.0. CROM alone+1299cyc/token (+36chained/+39cold),1.082us,0.451% predictedratecost. Combined+16919cyc(+6.241%),rate-5.874% vsheldsource. Streamoccupancy SiLU+4/layer(+144token), but residual x schedules each-22/layer, whole invalid2hopcounterfactual delta-1462; no rate-gain claim. Current token priceHELD; nonDV/source transport/head heldfixed, newmethLS407 separate. Record results/uarch/qwen_s8_crom_price_1025 on codex/s8-mat-1025.

## CODEX handoff 2026-10-25 03:35 PDT
SFU extension WIP0854ca24e preserved, intel2codex-s8-crom-sfu-1025 unit2689683 stillcompiling; no verdict/OKmarker. MAT/model complete5e92da909; seeCODEX-LOG handoff.

## CODEX notes — Handoff to Claude 2026-10-25 03:35 PDT
Parked on CLAUDE RESET. Complete branch/results/job inventory in CODEX-LOG Handoff QC token / bound S8 sublane. Combined branch codex/qwen-token-integrate-1025@57e2d3bb6; methreceipt801fdc3fd; wavefrontsmoke bc11ef2db. Running: intel2 codex-qc-crom-row-1025 build, intel2 codex-qc-mat-all-1025 (112cases), epyc3 codex-qc-wavefront-run-1025/both; SFU child records own job. Future CROM calibration watcher STOPPED, scripts safely staged. No new owner question.

## CODEX notes — 2026-10-25 05:59 PDT handback
Collected inherited MAT all112/112 PASS and SFU align clean6336checks/320outputs0mismatch + mutant480 caught. CROM row binary built04:37; inherited representatives residual28/28, QK7/7, SiLU2/2 PASS. Own redundant calibration mistakenly truncated prior slice_calibrate.out before discovering existing gates; own exact unit stopped, previous ages and representative results intact. Own full-stage correctly refused empty calibration stdout (exit6; no259sim). Detailed correction/paths in CODEX-LOG. No source changes or new live jobs; explicit START next.

## CODEX 2026-10-25 13:52 PDT — full projection vehicle
Old XT1 numericcids0..3 cover only4/8chunksfirst128/768rows. W5representativecarve is boundeddebug, not fullQKV. Current TOKENS owns whole377QCtop+wholeKV pair; actual48cluster/768tile/7680mask prep PASS0layoutmismatch using realP8191L0_mat_qkv.npz x+weights/gold and recovered exact8f48ROM image intel1:moved/home__ubuntu__scratch/qc-tok/xt1/img. Helper-onlyREADY8a0fc9c610, no pairedRTLelab/tokenPASS. Canonical268posthookbind0errors, source50a17ec84f plan441d1401 must travelwithmatchingregisteredPHYschema/tools. LegacyECCF/newplan schemaFAIL diagnosedversionmix, not waived; olderECCF268 CB16fails48intrapart n_a alignmentlegs. WholeQC ABI has onlyreset/START/clocks/UCIe services; realactivationmustenterthroughnativeKVbootprogram path, nointernalcontrolforce. Explicit PHYbehavioralproxy/physicalprojection and currentKVparentIDgates remain KV-owned blockers.
