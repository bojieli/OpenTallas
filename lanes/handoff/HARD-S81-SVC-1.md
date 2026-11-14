# HARD-S81-SVC-1 handoff (S81 svc family, DIEVIEW-S81 F3, R-CAP-3; Fable lane; COORD) -- started 2026-11-13 06:14 PST

## Scope
- 16 svc items (svc_hi/lo dsdv_svc_rs*, pvso_entry), 242 failed launches, never placed in the wave.
- Brief: (1) flop memory -> generated macro (sim + interface equivalence); (2) R-CAP re-size/split; (3) floorplan in the core-shape
  freeze; (4) private ot-run kit to place + GRT, renders viewed; (5) READY branches (RTL/macro, plan delta), adopted after 11-15 04:00.

## Worktree / files
- epyc7 /srv/opentallas-scratch2/claude/wt/hard-s81-svc-1, branch claude/hard-s81-svc-1-1113 off origin/main 4a5e3dcf7e (own clone).
- Work dirs: epyc7 /srv/opentallas-scratch2/claude/hard-s81-svc-1/ (v5/plan_A.json = ready12b-A 18c864518844);
  epyc2 /srv/opentallas-scratch2/claude/hard-s81-svc-1/ (kr/ = kit RTL + closure of the 16 types; fitgate/ = private copy of the MEM v2 gate).
- Logs: intel2 ~/tmp/hard_s81_svc_kr_all.log, ~/tmp/hard_s81_svc_fitgate.log.

## Findings (all [CHECKED] by me on 11-13 unless marked)
1. The memory is ALREADY a generated macro since 11-03 (MEM v2, main): attn_staging 8 lanes -> 8 x ot_sram_1r1w_160x265_m1_r0c0,
   land -> 12 x 160x256, pmem -> 4 x 256x256_m1, pvq -> 17 x 32x128 (sram_gen via tools/mem_compiler/build_s81_svc_fit_1103.py; views in
   physical/asap7_memory_macros_v2; gate results/rtl/s81_svc_memory_fit_1103/run.sh; +0 cycles). The plan contents of every svc type
   already place these 45 macros.
2. Why the wave still sees flops: the macro form is applied by a post-bind step (tools/die_plan/s81_svc_memory_closure.py --kit-rtl)
   that was one line of physical/die_plan/s81/kit_wave/kit_rtl.sh (kit_rtl mode "script"). KIT-OPS-1 moved dies.s81.kit_rtl to mode
   "bind" at the ready12b-A switch (11-12 21:46); mode "bind" calls bind.py kit-rtl directly, so the closure is skipped. Evidence:
   kit_wave.json dies.s81.kit_rtl.mode = bind; epyc8 .../items/svc_hi_dsdv_svc_pvso_entry__t1/attempt_9/rtl/*_bound.sv has
   SRAM_MACRO(1'b0) and no memory_closure.json; gen_lint.json memory_bits FAIL (4 x 160x265 + 512x512 + 640x256 + 8x2120).
   hold_items had no svc entry, so the 16 items were still relaunching at 06:2x.
3. The memory was never the wall. R-CAP (cap_estimate.project on plan 18c864518844):
   - form of record (64 attn_hcore + 8 sx_hrow hard cores, rest flat): 4.14-4.18 M mapped cells (CODEX 11-07, quoted) -> place 4.4-4.6 M, 19-20 parts.
   - provider form A / svc v5 (26 boxes hi, 58 lo; parent soft 228,760 hi / 381,961 lo, svc_prov_meas_1109.json): still OVER on the
     1442.88 x 2747.52/2851.2 outline: place 597k (hi rs t1), 802k (hi pvso_entry t1), 822-852k (lo). The outline term dominates
     (16.6-20.6k pins and 174-310 macros x 2.1 mm half perimeter = 350-590k repeaters).
   - so R-CAP needs BOTH: provider hard cores (R-CAP-3 point 3) AND the tile cut along Y into 2-3 partitions (point 2). Even split
     of the hi form A: 2 parts 241k each, 3 parts 148k each.
4. History that the brief did not carry: svc v5 provider plan (S81-SVCRS-3, events 11-09..11-11) was dropped at ready11r (strict bind
   failed: prov_1109 views did not exist). S81-SVCRS-4 then built all 21 provider rows at the exact v5 outlines: 12 SIGNED, 9
   LOCAL_PASS_NEEDS_PARENT; views still on epyc9 /srv/opentallas-scratch2/claude/s81-svcrs-4/prov/run (46 GB; lanes/S81-SVCRS-4-ROWS.tsv).
   ready12b-A kept the svc_lo +77.76 um growth (2851.2) but has no provider box: svc_prov_event_1109.py refuses plan 18c864518844
   ("not the base outline": it expects svc_lo 2773.44). Open design item S81-A1 (staging SRAM -> transposer 2.15-2.89 mm in one cycle,
   SRX relays, +16 cycles per pass) was never built (S81-SVCRS-3 stopped on a limit 11-11 03:39).

## Done
- 06:14 ASK KIT-OPS-1: hold the 16 svc items (queue, on origin).
- Flow fix in the worktree (not yet committed at this line; see State): kit_rtl_post.sh shared by both kit_rtl modes + kit_wave.py
  kit_rtl_post_cmd + test_kit_wave_kit_rtl_post.py.

## State / next (update below)
- 07:0x: commit fe4468028e in the worktree (not pushed yet): kit_rtl_post.sh + kit_wave.py kit_rtl_post_cmd + 6 tests (pass).
- KIT-OPS-1 06:31: the 16 svc items are HELD (hold_items + route_hold_items, SVC-MACRO-1113). Release = me / S81 die owner.
- MEM v2 gate re-run on a private copy (epyc2 fitgate/, inputs sha-equal to the committed list): FIT_PASS 20,000 edges, 5/5 mutants FAIL.
- Closure on TODAY's bound (ready12b-A bind out_main_7073a6b4a5_b, bind.py kit-rtl as the wave runs it): running for all 16 on epyc2
  (kr_all.sh, 4 at a time, about 12 min per type); hi rs t1-t4 APPLIED. kit_rtl_post.sh run on the real closed kit of hi t2: PASS.
- Running: epyc2 genproof.sh svc_hi_dsdv_svc_rs__t1 (gen + GEN_LINT from the closed kit RTL; intel2 ~/tmp/hard_s81_svc_genproof_hi_t1.log).
- NOT done: steps 2-4 of the brief (split, floorplan, place/GRT kit). See the PLAN post for the form decision COORD has to make first.

## RESUMED 2026-11-13 07:27 (COORD: Fable limit reset; I own svc again; read lanes/handoff/SVC-MACRO-2.md HANDBACK 07:26)
- Checked myself after the handback: closure APPLIED 16/16 on the ready12b-A wave bind, 0 kit-rtl failures (intel2 ~/tmp/hard_s81_svc_kr_all.log);
  GEN + GEN_LINT svc_hi_dsdv_svc_rs__t1 PASS, memory_bits PASS (~/tmp/hard_s81_svc_genproof_hi_t1.log); MEM v2 sim gate PASS, 5/5 mutants fail.
- Memory part (brief step 1) = DONE by READY claude/svc-macro-2-1113@3856aafc01 (my fe4468028e on main 24b08535da; on origin). No new macro, no cycle change.
- Codex recover output reviewed by SVC-MACRO-2 and kept as step 1 of the form: epyc7 hard-s81-svc-1/v5/plan_provider_recover.json, status
  PRIVATE_UNGATED, 14 rs types, die geometry unchanged; pvso_entry t1/t2 OPEN (+57.24 um row offset, new landing placement); reset contract not re-solved.
  Branch claude/svc-macro-2-form-1113@ff8154806c (script only). Untracked Codex files still in wt/hard-s81-svc-1 (not mine, left).
- NOT started: RTL band cut (dsdv_svc_rs_c / ot_s81_svc_attn_s), sim + LEC of the cut, plan event, floorplan, private place + GRT kit.
  All gated on the A/B ruling asked 2026-11-13 07:27. No job of mine is running. Hold SVC-MACRO-1113 stays.
- Next for whoever continues: (1) ruling A/B; (2) band wrapper RTL + benches (tb_svc_h8_protocol, tb_svc_srx_attn, svc mem benches) + LEC with
  boundary flops mapped + R-RTL-6 latency rows; (3) plan event = provider-recover + band partitions + pvso_entry + reset contract, R-STREET
  (final on main 5eefdbe2fa) on the band streets; (4) one band part to place + GRT privately, renders viewed; (5) READY after 11-15 04:00.

## 2026-11-13 07:53 option A work (COORD ruling: 4 band partitions, registered boundary, provider cores per the recover plan)
- The recover plan IS the H8 form (32 attn hard cores per tile, boxes in the 4 freed rows): it needs -DOT_SVC_H8 -DOT_SVC_H8_REUSE_RT2
  -DOT_SVC_MERGE_H4 -DOT_SVC_ATT_MEM_MACRO in the S81 bind (today the bound is H16 with none of them). No svc row growth is needed for the boxes.
- SIZING, measured by me (ORFS asap7 synth, hierarchy kept, current main svc RTL, H8 provider defines; epyc2 hard-s81-svc-1/hk/hk_hi,
  hk_lo/run/reports/asap7/*/base/synth_stat.txt). hi u_rsv: 507,956 cells; boxes TRX 4 x 27.9k, SMC 66.3k, SMR 40.4k; SOFT 289,709
  (11-09 figure was 228,760). Soft by owner: dsdv_svc_att own 120,613; engine ot_s81_svc_attn_s own 46,811; rs_c own 46,967; sx 21,907;
  sms 18,049; smh 8,962; gw 3,587; the 4 tile wrappers 5,626 each. lo u_rsv is the same within 1% (irg/ctrl/etap come on top).
- So a band (tile + transposer + merge) carries only about 6k soft cells + its boundary flops. 4 bands alone leave about 267k soft in the rest:
  R-CAP projection 451k OVER. The service logic needs its own cut at the u_att module boundary:
  band x4 about 27k each (OK); S_att (att own + engine control + its 76 SRAMs) about 261-269k (TARGET, under 400k); S_rs (rs_c, sx, sms, smh, gw
  + SML/SMD/SMC/SMR/sx_hrow) about 179k (OK). Pin counts of S_att / S_rs are my estimates (12k / 14k).
- RTL written (worktree branch claude/hard-s81-svc-1-band-1113 off main 5eefdbe2fa, not committed yet): rtl/dsrom_sys/s81_svc/ot_s81_svc_band.sv
  (transposer + tile + merge, every input captured, outputs registered), BANDX / BANDMUT in ot_s81_svc_attn_s (as-built names unchanged at 0),
  -DOT_SVC_BAND in dsdv_svc_att, tb_svc_srx_attn + svc_srx_lockstep.py --band (expected shift n = SRX + 2: scores +n, P.V +2n).
- RUNNING: lockstep proof epyc2 hard-s81-svc-1/ls/w_band1 (--dut s81 --srx 1 --band --mut 1,2), log intel2 ~/tmp/hard_s81_svc_ls_band1.log.
- NOT done: u_att service cut (handshakes q/kv/p ready cross it: needs skid stages, see tools/landed_parent/lp.py and dsdv_svc_rs_lp for the
  existing landed form), SM boxes and lo IRG placement per part, LEC, plan event (pvso_entry, reset contract), floorplan, place + GRT.

## 2026-11-13 08:29 band RTL proven and pushed
- READY claude/hard-s81-svc-1-band-1113@2a0fecefcd (parent origin main 5eefdbe2fa; on origin). Files: rtl/dsrom_sys/s81_svc/ot_s81_svc_band.sv (new),
  ot_s81_svc_attn_s.sv (BANDX / BANDMUT), dsdv_svc_att.sv (-DOT_SVC_BAND), test/tb_svc_srx_attn.sv, test/svc_srx_lockstep.py (--band).
- Proofs (epyc2 hard-s81-svc-1/ls/{w_band1,w_srx3,w_base}; verilator v5.032; seed 11, 10 jobs, 419 score beats, 80 P.V beats):
  (1) band form (SRX 1 + BANDX) vs as-built engine: all beats bit-identical in value and order, first job +3 / +6, bank-set checker 0 errors,
      BANDMUT 1 and 2 both break the data (lockstep.json status PASS);
  (2) band form vs the SRX 3 engine (the form S81-ARCH-RTL-2 proved 11-11): all 1,218 traced events (job/q/kv/p accepts, score and P.V beats with
      data) identical INCLUDING the cycle -> the band is cycle-exact SRX + 2;
  (3) defaults off: unpatched main vs patched source at BANDX 0, SRX 0 and SRX 3 traces sha-identical.
- Latency bookkeeping: per svc pass scores +(SRX+2), P.V +2(SRX+2) against the as-built schedule, the SRX rule with n = SRX + 2. The die schedule
  (compose_tok_ds PIO / KPV) must move by n; R-RTL-6 latency rows are owed with the plan event (n is fixed there, SRX = plan station hops).
- NOT done: formal LEC of the band form (sequential; sim proof only), service cut S_att | S_rs, plan event, floorplan, place + GRT.

## 2026-11-13 08:30 STOP POINT (context budget; no job of mine running)
State of the brief: (1) memory macro DONE (train 49). (2) size: measured, form = 4 bands + S_att + S_rs (+ S_idx lo), amendment asked 07:53,
no COORD answer yet, I proceeded on it. Band RTL READY 2a0fecefcd. (3) floorplan, (4) place + GRT, (5) plan READY: NOT done.
Floorplan starting numbers (hi tile 1442.88 x 2747.52, from v5/plan_provider_recover.json rows; NOT validated against R-STREET):
- band k = one attn core row (8 cores, 259.2 tall) + the box row above it. Row pairs at y 34.56/311.04, 587.52/864.0, 1321.92/1598.4, 1874.88/2151.36.
  Band outlines in Y: B0 [0, 587.52), B1 [587.52, 1140.48), B2 [1321.92, 1874.88), B3 [1874.88, 2419.2). sx_hrow strip [1140.48, 1321.92).
  Top strip [2419.2, 2747.52] = 0.474 mm2 for S_att (76 SRAM about 0.15 mm2 + 168k soft).
- PROBLEM to solve first: in the recover plan each box row also holds 2 SML + 1 SMD (S_rs logic). Partitions are rectangles, so either
  (a) SML/SMD go logically into the band (needs a registered SM cut smh <-> g_l/g_p: +1 each way on the softmax lanes, new RTL + bench), or
  (b) SM boxes move into a grown S_rs region next to the sx strip (8 SML 103.68 wide + 4 SMD 69.12 + SMC + SMR = 1,252 um of boxes: two rows
      with R-STREET streets; svc rows grow about +300 um, pre-approved) and each band keeps TRX + 2 H4 only (band soft about 9k).
  I recommend (b): no new RTL cut, SM timing untouched, bands become identical for all 14 rs types (one band type, one sign-off).
- Service cut S_att | S_rs = the u_att instance of dsdv_svc_rs_c. Its q / kv / p handshakes use ready signals, so a registered boundary needs skid
  stages; the generated landed parent dsdv_svc_rs_lp (tools/landed_parent/lp.py, 8 landed crossings, record
  results/arch/s81_dv_1016/svc_rs/lp/) is the existing proven form of exactly this cut: start there, do not hand-write it.
- Band private kit: follow HARD-S81-DSDV-1 xs4h (physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py --module --recipes, LEF contract,
  macro_sites) with module ot_s81_svc_band, children = 8 ot_s81c_attn_hcore (signed rt22m_hx2 views), ot_hdc_v41x_attn_tr_x (S81-SVCRS-4 trx rows:
  trx0/trx24 SIGNED, trx8/trx16 LOCAL_PASS_NEEDS_PARENT), 2 ot_s81_svc_merge_h4 (SIGNED). Band pins about 1.75k in / 530 out.
- Bind defines for the form: OT_SVC_H8 OT_SVC_H8_REUSE_RT2 OT_SVC_MERGE_H4 OT_SVC_ATT_MEM_MACRO OT_SVC_SRX=<hops> OT_SVC_BAND (+ OT_SVC_NSTAGE=3
  if back-to-back slip matters). pvso_entry t1/t2 and the reset contract are still open in the recover plan.
- Codex untracked files in wt/hard-s81-svc-1 (delta_svc_provider_recover_1113.py, type_split.py): not mine, left untouched; the script is on
  origin as claude/svc-macro-2-form-1113@ff8154806c.

## 2026-11-13 10:46 band v2 READY, service cut pushed (bench gap), band kit v1 result, kit v3 running
- COORD rulings 08:3x-09:5x: form approved (4 bands + S_att + S_rs, + S_idx lo); SM boxes into a grown S_rs region; band RTL train 55; then
  band fixes (centre transposer, 43.2 inter-row channel, registered reset tree, registered merge valid, load pipeline, M7 ceiling).
- READY claude/hard-s81-svc-1-band2-1113@aef8068c0b (on 2a0fecefcd): reset tree (root + 3 leaf flops), MREG merge input register, CAPD 2.
  Lockstep SRX 1: 419 score / 80 P.V beats bit-identical, first job +4 / +9, set checker 0, both controls caught; define-off trace = main.
  Latency with -DOT_SVC_BAND: scores +(SRX+3), P.V +(SRX+4) against the p feed; per pass scores +(SRX+3), P.V +(2 SRX+7).
  NOT fixed in RTL: the tile fans reset and the load word out to its 8 cores inside rtl/hdc (one port each); that needs a tile change.
- Service cut: claude/hard-s81-svc-1-attcut-1113@52dc675ba9 (on 2a0fecefcd), dsdv_svc_att_cut, -DOT_SVC_ATTCUT. Bench 3 seeds x 200k cycles:
  0 mismatches (qrq +1, other lanes +2), CUTMUT 1 caught, CUTMUT 2 MISSED: the random stream makes 0 P.V beats (fault 99 percent of cycles),
  so the P.V and SM lanes are NOT exercised. Owed: programme-driven bench (tb_svc_h8_protocol stimulus) before any kit uses it. NOT READY.
  The landed parent dsdv_svc_rs_lp was not used: it was generated from the 10-18 flat form dsdv_svc_rs_f, stale against today s dsdv_svc_rs_c.
- Band kit v1 (sub-lane BAND-KIT-1, Opus; epyc2 /srv/opentallas-scratch2/claude/band-kit-1): 9,658 synth cells, 11 cores, 28-31k movable after
  place; my brief s floorplan overshot its outline (grown to 1442.88 x 639.36); GRT M7: 552 overflow cells on M6 in one row over the cores,
  M5 ceiling fails (core clk pin is M5); setup about -0.51 ns est. Renders viewed by me: one thin trunk along the core row top, rest green.
- Band kit v3 (new RTL, transposer centred, 43.2 channel, M7): RUNNING in BAND-KIT-1 (GRT cap about 11:13). Renders will be in localhost
  scratchpad band_kit/v3/. Known item: 15.12 um streets between the 8 cores (lattice width 1442.88 leaves no more).
- NOT started: pvso_entry t1/t2, reset contract, bind defines, plan event, grown S_rs floorplan.

## 2026-11-13 11:03 tile pair READY; sub-lanes running
- COORD 10:5x: band v2 = train 63; service cut needs a programme-driven bench (P.V + SM controls caught) before READY; do the tile change in rtl/hdc.
- READY claude/hard-s81-svc-1-tilepair-1113@ba62fe88e1 (on band v2 aef8068c0b): ot_s81c_attn_tile_hc_h8_rt2 PAIR 1 (-DOT_S81C_TILE_PAIR):
  4 load-sender copies (one per core pair, same edge, no cycle moves) + reset registered once per pair and in front of u_expand (reset +1 edge).
  Bench tile_pair_bench.sh: seeds 1-3, 16,000 cycles, 3 warm resets, 1,560 output beats each: 0 mismatches; control 10.8k mismatching cycles.
  No signed tile view exists (the tile wrapper is soft logic of the band; the signed object is the head core, untouched): the band kit is its physical proof.
- Sub-lanes (Opus): CUT-BENCH-1 = trace-replay bench for dsdv_svc_att_cut with CUTMUT 2 (P.V) and a new CUTMUT 3 (SM row lane), epyc2
  /srv/opentallas-scratch2/claude/cut-bench-1; BAND-KIT-1 = band kit v3 (band v2 RTL, no tile pair yet), epyc2 band-kit-1.
- Next: band kit v4 with the tile pair define once v3 reports; then pvso_entry, reset contract, bind defines, plan event, grown S_rs region.

## CODEX notes 2026-11-13 13:45 PST
Direct takeover in existing worktrees. CUT-BENCH-1 programme proof collected: seeds1/2/3 nominal0 mismatches,0 faults; each160 P.V words,20 SM row beats; CUTMUT2 caught164 cycles, CUTMUT3 caught37. This closes the earlier unexercised P.V/SM gap. Source+bench+logs pushed hub as claude/hard-s81-svc-1-tilepair-1113@7140618b36 (7 new files only; inherited tile-stage dirty edits excluded). Original OT_SVC_ATTCUT integration remains52dc675ba9; no plan/wave change. Band v5 E2 unitoth-ubuntu-3630374-1794605544 healthy in placement; tile3 lockstep E2 unitoth-ubuntu-2900932-1794605007 healthy. Next: collect these, inspect placed band, service split floorplan.

## CODEX combined tile proof diagnosis
Inherited tile3/ls fails nominal (BSC 425 vs 419, PV 72 vs 80): the helper passed OT_S81C_TILE_STAGE but omitted the enclosing OT_S81C_TILE_PAIR, selecting PAIR 0 while tags assumed PAIR 4. Fixed helper in the E7 worktree and E2 tile3/root. New proof via ot-run E2 unit oth-ubuntu-610605-1794606419, intel2 frontend 3937369, log ~/tmp/hard_s81_svc_ls_tile3_pair_codex2.log, outputs tile3/ls_pair. Initial own unit 578107 failed CLI missing --root, corrected without RTL change. Failed artifacts retained.
Viewed E2 band-kit-1/v4/layout_review/place/layout.png and density.png: eight-head macro wall with 15.12 um gaps, sparse upper floor, narrow W-input streets. R-STREET plan adoption remains BLOCKED until geometry redesign. Band v5 inherited physical proof retained; no new route. Full service-floorplan packing limits are under OWNER? in CODEX-LOG and sent to DIE-S81-89.

## CODEX notes 2026-11-13 14:08 PST: band timing and staged tile next form
- Inherited band v5 completed PLACE/CTS. Viewed place layout.png and density.png at epyc2 band-kit-1/v5/layout_review/place. Eight head cores form a wall with 15.12 um W-input streets; upper floor sparse. SMELLS: pin_track_use 0.502, fanout_spread 1498.3 um. CTS setup -448.83 ps, worst d_q[0][1766] -> g_in[7].g_r.qw[97]. Existing GRT continues; no new physical run launched.
- Corrected tile3 combined proof: FAIL retained at tile3/ls_pair/lockstep.json. All 419 score payloads exact; 80 P.V beats but wrong payload on beats 24-31 and 40-55 (jobs 3/5/6). No core fault or set-check error. First-job shifts +5/+11 correct. Both controls diverged; only own mutant binary PIDs 1155927 and 1155918 stopped after divergent payloads, avoiding a redundant 900-second tail. Nominal finished 1255 cycles. Tool falsely exited 0 on FAIL; fixed sys.exit in existing worktree.
- Small four-job NSTAGE=3 nominal diagnostic now running through ot-run on epyc2. Intel2 frontend 71084, log ~/tmp/hard_s81_svc_ns3_diag_codex.log, outputs tile3/diag_ns3. Diagnostic only, no mutant/gate credit.
- Conservative private PAIR 5 form added to existing worktree: five distributed per-core input stages (four corridor hops plus one drop to the W pins), matching reset and merge-tag delay. Actual global event is not adopted. Added staged expander-fault alignment; odd P-group bench exercises it. Five-stage tile miter/control job: epyc2 unit oth-ubuntu-1270819-1794607278, intel2 frontend 4182619, log ~/tmp/hard_s81_svc_tile_reach5_codex.log, outputs hard-s81-svc-1/tile_reach5. Earlier three-stage legal-input proof unit oth-ubuntu-1246582-1794607096 still progressing, no kill/restart. Source edits remain uncommitted pending these results. Patch constructors are in epyc7 hard-s81-svc-1/patch_tile_reach_codex.py, patch_tile_fault_codex.py, patch_tile_reach5_codex.py.

## CODEX SVC native RT2 diagnosis correction and fix
The old helper summary `faults=0` counts expected golden flags, not actual observed DUT protocol faults. My earlier no-fault wording for the native-engine run was therefore incorrect. Frozen archive trace proves actual expander af becomes1 at baselinecycle80 (Ploads at78 and79 while replaypending) and DUTcycle88. This producer/consumer II mismatch corrupts the first3lookahead Pblocks; merge tags are correct. Original FAIL verdicts and traces retained.
Current private fix uses a STATIC II2 load calendar: phase0 after localreset release admits nativeP/Qloads; phase1 is always reserved forRT2replay, independent ofrequests/acceptance. No new queue, credit or request-drivenphase. Source/default/non-nativeforms retain their previous slots. Productionprogramme must be rescheduled and measured before adoption; privatehandshakebench qualification alone cannot authorize production.
Fresh guarded native reference/DUT programme with PAIR5 is running: epyc2 hard-s81-svc-1/native_rt2_calendar, intel2frontend435775, log~/tmp/hard_s81_svc_rt2_calendar_programme_codex.log. Independent actualcalendar+actualexpander12packet staticstorage/readback/control bench running: epyc2 calendar_probe/out, unit1559478, intel2frontend444004, log~/tmp/hard_s81_svc_calendar_probe_codex.log.
PAIR5 isolated productiontile proof now PASS all3seeds (16kcycles,3warmresets,2oddPgroup controls,1560nonzerooutputs each,0nominalmismatches; malformed-load mutant8181/8101/8193mismatches). Source00cae87333 pushedhub. No P&R/PORchange; bandv5inherited GRT stillrunning.

## CODEX SVC engine component / static producer milestone, 2026-11-13
Guarded native engine: all 419 score and 80 P.V payloads exact; both controls caught. First-job shifts are +9 score / +20 P.V cycles. Original +19 timing receipt remains FAIL; fresh analysis-only lockstep_priced_ii2.json records the explicit slot price. Nominal ends at 1,336 cycles; guarded reference ends at 1,276. Only our two divergent mutant binaries 1604552 and 1604546 stopped after witnesses. No simulation repeated for repricing.
Calendar rule: A(t,phi)=t+((phi-t) mod 2); load shift=A(t+n,phi)-A(t,phi), then tile adds n and merge adds 1. Only n=9 measured in the engine. Small odd-origin transport control running, intel2 frontend 717396, log tmp/hard_s81_svc_calendar_round_codex.log.
Model-only +9/+20 price: AR 842.11438 (-0.081404%, +1,160 cycles), MTP 2712.92382 (-0.022015%, +405). Optional cut +2 each: AR 842.01983 / MTP 2712.79110. Invalid native-reference correction kept separate, no POR adoption.
Production Q/P reschedule remains required and private: helper owns static Q index/phase and phase-one P pushes in actual dsdv_svc_att, plus uncalibrated compiler records. KV release stays one beat per cycle; no ready-driven production issue. No new P&R. Source through 7239ea0c89 on GitHub; timing follow-up d4eb5ad2b8 on hub. Merge agent only has additive commits 7140618b36 and 51b2644284 as READY; combined forms remain HOLD.

## CODEX SVC production programme and private packing, 2026-11-13
Actual outer decoder + native PAIR5 engine fixed-T32 programme PASS in both GO phases: Q 8, KV 8, P pushes 4, P accepts 4, 8 nonzero score beats, 8 nonzero P.V beats, 40 drain words per case, protocol fc 0 and observed expander af 0. Independent integer oracle checks 1,024 FP32 fields, 0 errors. E7 hard-s81-svc-1/native_programme/out_nonzero/{run.log,oracle.json}. Preloaded P and test-only PO/PVO do not calibrate real SM feedback or global PIO/P_ARR. Next staged score trace → actual SX transport → actual fold2 → macro P buffer → native P source uses production sid 10 / tile 0 for H8 pass 0.
Private control-only S_att alternative: 66 measured provider rectangles plus assumed 328.32 um control/memory strip pack with +345.60 um per-partition Y, 43.20 um streets and 8.64 um origins. Viewed drawing remains BLOCKED FOR ROUTE: scattered provider locality, unbuilt source cut, unmeasured parent face count and unplaced control memories. Small-growth heuristic did not place all boxes. Die row multiplicity not priced; +345.60 um is NOT a die-fit claim. Evidence E7 WT results/geom_review/svc_control_cut_packing_1113. Approved four-band plan and POR unchanged.

## CODEX SVC additive source and selected feedback milestone
91cedfcd74 isolates both native replay calendar and production Q/P reschedule behind explicit OT_SVC_NATIVE_RT2_CALENDAR. Without it, actual decoder and engine preprocess exactly to pre-calendar source; with it they match the numerical-qualified 4b3430fb52 elaboration. Cached static producer nominal/macro and malformed-control proof PASS. Review found 13 legacy synthetic Job AttributeErrors; 0db71fea0e fixes source fallback to False and adds true/false metadata checks. Existing compiler tests now 28 PASS. Portable check tools/s81_dv/svc_rs/check_native_rt2_optin.py also proves default compiler bytes/cycles/done-span equal current main 9556712 for H16/T128 and H8/T32,T128. Merge agent reviewing additive source; global calibration/POR/geometry remain held. GitHub mirrored through 91ced; canonical intel2 push through 0db71 running.
Actual selected feedback partition PASS at E7 hard-s81-svc-1/score_feedback/out, unit 2302260-1794614282. Real native nonzero score trace through actual 16-node SX, production sid 10 / tile 0 SE assembly, actual fold2 SM, macro P buffer, native P source, actual SX return and packet packer: 8 root/tap scores, 2 SE rows, 2 nonzero SM writes, 8 P words, 1 header, 0 missing/errors/faults. Independent raw exponential oracle all 32 coefficients FP32 1 / BF16 3f80; later SO normalization not claimed. Dropped source control caught SX fault 002a. GO 128; scores at root 257..264, tap 277..284; SE 281/285; SM writes 391/393; fixed test PIO 800 gives P source 810..824 and packet header 853/body 854..868. Test PIO is not production calibration. Next actual returned-P native replay is owned by helper using existing archive/runtime vectors; no giant native rebuild.

## CODEX handback 2026-11-13 17:15 PST
CLAUDE BACK; no own jobs live/newlaunches/adoption. Full source/results/failures/remaininggates: ~/coord/handoff/codex_svc_20261113_1715.md. Hub/GitHub through9d2710b8c2; completedallheadT32checkpointfollow-up pending. T128NOTRUN. FullLOpackblocked/rootbudget;276.48IRGviewmissing; noPORorroute.

Completed safe checkpoint c3bd38ae82 is now on canonical hub branch claude/hard-s81-svc-1-tilepair-1113. Completed all-head T32 source/evidence only, no new test/launch/adoption. Evidence results/svc_attcut_1113/allhead_feedback_t32/{README.txt,staged,native}. T128 runtime support NOT RUN, T640 deferred. All descendant work parked, no own live jobs or pending owned edits; unrelated donor files untouched. Canonical GitHub mirror for checkpoint is in flight; intel2 command git -C ~/OpenTallas push origin claude/hard-s81-svc-1-tilepair-1113.
