# S81-DIE11 (10-20 13:20-) — S81 release die: mu7 plan, M8 die chain, pilot collection
Takes over from S81-DIE10 and CODEX-S81-1245. Tree lines: S81.BIND.2.P, S81.GRT, S81.STA, S81.CLK.

## 10-20 ~13:50
- ROOT 66736dcff (60d0f9369: M8 opt-in RC/top layer + shallow payload equalizer) is ON origin/main (98070b1b5). Die STA in
  the M8 cases: `set_wire_rc -signal -layer M8` in place and in sta_{tt,ff,ss}; repeater step `--rc-layer M8`; signals M2-M8,
  clock M5-M9; adjustment M6-M8 0.20. The corridor die_repeaters (804d68ef6) are NOT on main, so the mu7 dieflow ref is my
  branch claude/s81-die11-1020 @96e76497c = 804d68ef6 die_repeaters.tcl/step.py + main fclk_audit.tcl (payload equalizer).
- dv_plan `--rsv-vcol K` (96e76497c): K x 43.2 um added to every svc_rs column gap (vertical channels x 10.5-21.5 mm,
  the residual V spine of the M8 trial). Default is byte-identical (mu6 plan reproduced exactly).
  K=1: svc 1214.2 wide, gaps 153.2; K=2: svc 1176.4, gaps 196.4. Both keep 122 frames / 1130 ROM slots, over-reach 0.
  Model cut 0.5663 -> 0.6157 (one 260 um window: hrq_07+hrd_07+sg_07_09 fall in one bin; M2-M7 model, M8 not counted).
- LAUNCHED (parallel with the live M8 pilot): lanes/s81-die11-run_mu7.sh. Plan -> strict bind (branch + main checker)
  -> dv_rvcase --signal-top-layer M8 (CTRL/relay native views 12c132d60, PHY _k, dcc main 98070b1b5) -> repeaters ->
  GRT -> STA TT/FF/SS -> CLK. Runs on ep6 /srv/opentallas-scratch/claude/s81-die11/{mu7v1,mu7v2}
  (units oth-ubuntu-80104-1792528141 / -83514-1792528166; local clients log to lanes/s81-die11-mu7v{1,2}.otrun.log).
  Branch-checker DIE_PORT_BIND PASS 0/0/0 for both (9885 / 9893 instances).
- LEAD9 13:3x HARD CONSTRAINT: mu7 must keep 122 frames (116 frames = 201 stages vs 140). The script asserts
  n_frames==122 and rom_slots==1130 (FRAME_GUARD).
- idx3 (in-line dsdv_idx_rg2 readers) does NOT fit at 122 frames: the die is at reticle in W (31.5 um left) and H (0).
  The in-line reader row needs about 1.1 mm more band height over x 10.5-21.4 mm. That displaces exactly f_2R01, f_3L01,
  f_3R01, f_4L01, f_4R01, f_5L01 (s_3S and s_4S lose 2 each), and the losses cannot be spread to other slices.
  The corner strips beside the PHY (2 x ~20 mm2, empty) would hold the readers, but the in-line rq/rd would put ~19.9k bits
  into a 200-um channel. That needs a reader RTL change (non-inline client) first. Reported to LEAD9 (decision a/b/c).
  idx3 bind is also not ready in RTL. Owed: the slice `iq` query-source port, a bk_sel + dsdv_idx_vmux wrapper (vi_idx), and
  the qf parent/child tree links (ql/qc0/qc1) as die ports. MU.BAL.SX.3 stays READY (RTL), with the die rebind blocked.
- TOPK 648 quarters: the column-4 frames are 1137.4 apart with lanes W 17594-17685 and E 18414-18534, so bk_sel can be at most
  680 wide. Vertical-only growth (gaps 3 x 132.8) gives 680 x 3381 = 2.30 mm2 against the 2.94 needed. The R0 907.2 x 3283.2
  slot needs the column-4 lanes moved. That is not in mu7v1/v2 (bk_sel stays a 680 x 2882 stand-in). Next: decide whether
  the lanes go over the block on M8, or TOPK takes a smaller glue area.
- svc_rs density: unchanged by mu7v (the E/W faces are still 1344 tall; the N/S faces get 3-6 % shorter). The real fix
  stays the S81-SVC8 kit feedthrough.
- M8 pilot 2506475 (ep5 case_mu6b_m8_chain) is still in the repeater pass (started 12:51); not collected.

## Next (successor)
- Collect mu7v1/mu7v2 steps.log CHAIN_RC, case/out/grt_congestion.rpt per layer (vs mu5k 854,368 / trial 82,594 / pilot),
  sta TT/FF/SS, die_clock_check json. Bind the better variant; drop the loser.
- Collect pilot 2506475 the same way (task 3).
- Act on the LEAD9 decision for idx3 (a/b/c) and TOPK column 4.

## 10-20 ~14:05 LEAD9 DECISION: (c) primary + (b) fallback; TOPK uses the HQ3 slot (hk2l allowlist parked)
- mu7v1/v2 (122 frames) keep running as the die-closure vehicle. The non-inline readers go into the PHY corner strips later
  (additive, no frame moves).
- (b) fallback: launched STAND-IN GRT diagnostics (lanes/s81-die11-run_sgrt.sh, dv_diecase --bind standin, M8 signals and
  repeater RC) as an apples-to-apples pair: s116v1 (idxrd 3, 116 frames, rsv-vcol 1) and s122v1 (idxrd 0, 122 frames, rsv-vcol 1).
  These are GRT geometry only, NOT a die result. A real 116 GEN/strict bind is impossible until the idx3 die RTL hooks exist
  (slice iq source port, bk_sel + dsdv_idx_vmux wrapper, qf ql/qc0/qc1 tree links as die ports). Bind owner: LEAD9-S81 next session.

## OWED under MU.BAL.SX.3 (owner LEAD9-S81, next session builds the RTL): non-inline index reader interface spec
Goal: 8 dsdv_idx_rg3 readers (one per controller pair, ENG=1 engine, same 1036.8 x 1036.8 slot), placed in the PHY corner
strips (4 W: x ~7.5-11.7 mm, 4 E: x ~20.3-24.5 mm, y ~0.2-1.24 mm), as CLIENTS of the controllers instead of in-line on
rq/rd. 122 frames are kept, and svc_rs <-> ctrl rq/rd are unchanged (still 1,244 b per region straight down).
- Request (reader -> ctrl k, per region): one 64-b lane {v 1, rd-only cmd: PC 1, bank/row/col addr 30, tag 17, beats 4, spare}.
  Merged in dsfd_ctrl_rg2 by a STATIC slot calendar: the compiler gives the reader fixed request slots (no arbitration,
  no credits), and svc_rs requests never use those slots. RTL change: a ctrl request mux on a compiled slot bit, plus a
  reader-tag range in the read-return demux.
- Response (ctrl pair -> reader): the reader consumes at most 2 regions x (1 key / 3 cycles) x 544 b = ~363 b/cycle, so
  2 x 276-b lanes per pair (552 b) carry {r_data 512 of the slot-owned beats, tag/beat/fault}. That is 2 lanes per pair,
  not 2 x 562.
- Chains: query qi/qo (2 x 276) and score si/so (276) between abutted readers inside each strip. W group -> E group: one
  828-b crossing over the CTRL-top channel. qf stays W of reader 0; is_tail goes from the E group end to bk_sel W face
  (as now, shorter start).
- Channel load (CTRL-top/svc-bottom channel y 1524-1724 plus the under-frame strip y 1240-1786 beside the PHY), crossing the
  PHY edge per side: 4 pairs x (2 x 64 req + 552 resp) = 2,720 b. Plus the 828-b chain crossing once: 3,548 b over ~546 um
  of usable height (200 um channel + strip) = ~6.5 b/um, against ~27.9 tracks/um (M2/M4/M6 at the GRT adjustment, before
  M8) = 0.23. The in-line variant needs 19.9k b, ~100 b/um. FEASIBLE.
- Stations and cycles: pair-to-reader distance (nearest mapping) 1.07 / 3.19 / 5.31 / 7.43 mm, i.e. 3 / 8 / 13 / 18
  stations each way at 405 um. Each reader HBM read adds 6-36 cycles of round-trip latency (fixed per pair, static).
  Absorb it in the reader's run-ahead window (T0) and price it into the lower_bk schedule (job_rank_tree_rd start offset
  per pair). Chain W->E crossing: 8.5 mm = ~21 stations, +21 cycles on the score/query chain (once per job).
  Expected throughput change: none at P3 scan / P4 gather if T0 is raised by the round trip; must be measured.
- Bench obligations: rg3 production 2-region bench (scan P3 / gather P4 x seeds, fail-closed late cases as L20RD3),
  a ctrl slot-mux bench (svc traffic bit-identical with and without reader slots), mutants; native census; then the die plan
  option (dv_plan --idxrd 4 corner strips) and a strict bind.
