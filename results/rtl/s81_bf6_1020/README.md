# S81-BF6 10-20: BF front native-census redesign (N32) folded with the S81-RTAG router tag P231 -> P130 (SOQ)

Branch claude/s81-bf6-front-1020 (on claude/s81-rtag-1020 @52847c754). Tile dsfd_bf_front_roots (critical prefix
ot_v41_bf_: no REVIEW.json, no submit by the lane; PNGs + checklist to lanes/COORD-REVIEW-QUEUE.md).

## Why
The BF front failed the pre-gate native census before any RTAG change (SOQ 0 and SOQ 1 alike): max 3,224 loads on
one driver, 206 drivers > 32 (census/base_soq1_named/groups.txt, the rtag soq1 RTL re-synthesised with
`rename -wire` so flops keep their RTL names):

| class | drivers > 32 | max loads |
|---|---|---|
| gate-enable copies cen[k] (one kept copy per former gclk register block) | 10 | 3224 |
| FP8 half select i1_uh | 1 | 533 |
| x FIFO write decode (flop FIFO 8 x 547 b, up to 5 writers a cycle) | 51 | 532 |
| walker selects / state (wA/wB/nA/nB/fF, b_lo/b_hi, d_*) | 18 | 288 |
| x FIFO read pointer copies / read mux | 85 | 258 |
| go_e copies | 8 | 194 |
| reset nets (rst_q 174, seam relays 160, core 43, south 44) | 13 | 174 |
| configuration write decode | 10 | 123 |
| other registers (c_s0, fam, go_bf, xb_u, d_q) | 10 | 58 |

Reach > 405 um: impossible in this tile (116.64 x 198.72 um). Flop storage > 2 kb: the x FIFO only (8 x 547 = 4,376 b).

## Change (opt-in N32, `DSFD_BF_N32=1`; default 0 = unchanged)
Zero added cycles. Every copy is the same register function of the same inputs. RTAG SOQ=1 SWD=160 is in the same RTL.
- Gate enable: ot_bf6_cen_pool (rtl/v41rom/ot_bf6_n32.sv). It holds kept copies of u_z, one kept OR (ze_d = go_pin || z)
  per 32 leaves, and leaf copies with no reset (each loads 1 at every reset edge, as the async-set original holds 1).
  ot_bf6_ereg loads 16 bits per leaf: the x boundary / input registers, xbd_r, fw_*, i1 / i2x, block 8, 12 and 20.
  Every other block takes leaves from the cpm pool.
- go_e: 3 kept b_go copies feed 92 kept go_e copies, one per register group.
- issue: 21 kept prog_issue_q copies.
- Reset: 8 same-edge copies of the parent core synchroniser and 28 kept rst_q copies. The seam relays go to one per 32
  bits (RG 32), and the south programme register is split over 2 copies.
- Selects: per-group selects (walker restart / advance, need-walker step) are keep_hierarchy AND cells (ot_bf6_kand).
  With plain ANDs or (* keep *) wires, technology mapping folded the shared term back into every bit.
- Configuration writes: decodes registered from the pins beside b_cfg_a (b_sd / b_cd / b_s2d / b_gd), one copy per
  <= 16-bit table group.
- x FIFO: stored per slice (flat vectors).
  - Every write enable is a register: the exact next state of cen && fw_v && f_wr == e (or bm_r[b] && f_wr + bpre[b]
    == e). There is one copy per 15/16-bit write slice.
  - There is one kept one-hot read pointer per 30-bit read slice.
- Kept copies of fam, go_bf, w_ca_r, w_j, bn_q, bn_cnt / bn_tot, d_q / d_j, xb_u, c_s0, f_wr and fw_v, plus a kept second
  go lockup latch in the parent (go_pin_n) for the pools.
- soq: go / go_q / wp copies.

## Pre-gate native census (tools/ref_tile/native_census.py from origin/main; census/census_named_l.sh)
- Flow: ASAP7 RVT TT, ot_keep_regs, synth -flatten, rename -wire, latch map (cells_latch_R.v), dfflibmap, abc.
- Final RTL (this commit): **PASS max 32, 0 drivers > 32, 0 role errors** in both flows: census/final (plain abc, 73,208 roots) and census/final_orfs (the ORFS synthesis: abc_speed.script, dont_use xp/x1p/SDF/ICG, -D 770, abc.constr; 75,103 roots). The first gate (8a3f4e60c) showed the plain-abc pass is not enough: the ORFS flow found 18 drivers > 32 (max 85: w_q / n_q into the sbf lookahead, non-kept originals merged into their kept copies), fixed by keeping the originals and more per-group copies.
  The SOQ base was 75.2k cells; N32 is 81.1k.
- Iterations: 3224 -> 532 -> 294 -> 83 -> 72 -> 40 -> 35 -> 32.
- The rtag-era script had no latch map, so its 2,595 "undriven" role errors were the lockup latches. Base and N32 both
  had them.

## SAFE-DESIGN checklist (pre-gate; layout facts come from the gate packet)
1. Pins: RTL registers every port (pin_regs disabled with reason, as the closed kit). The reset lands in 2 stages at
   the face (OT_RST_LAND).
2. Reach: PASS by geometry (max Manhattan 315 um < 405).
3. Fanout: PASS. Census max 32. Kept copies were verified post-Yosys under their flat RTL names (g_cpm.u_pool.g_l[k],
   g_gokn.g_g[k], g_rk.g_j[k], ...).
4. Depth: from the gate (TT) report.
5. Storage: x FIFO 4,376 b in flops, WAIVED with a reason:
   - Each cycle it takes up to 5 writes (one FP8 beat or 4 BF16 slices) and one same-cycle combinational read.
   - The smallest macro (ot_sram_1r1w_64x512) is 1W. An SRAM version needs banking plus a read-latency change.
   - It is now banked per slice with registered write enables, and no runtime-indexed flop array remains.
   - The other tables are < 2 kb: so_label_q 672 b, configuration about 600 b.
6. Floorplan: no macros. Exact closed sub-slot 116.64 x 198.72 (1.70:1) with a full std-cell band. Util comes from the gate.
7. Clock: 5 related roots (ck, io_clk, io_n, io_w, io_e) as the closed kit. Spread <= 80 TT/FF comes from the gate.
   io_hold_margin 0.03.
8. Schedule: N32 adds no cycle. SOQ contract (compiler, S81-RATE3): last partial of phase k < go_{k+1} + 160 edges.

## Behaviour (Verilator 5.050, commit 515864134 RTL; bench/)
| bench | case | result |
|---|---|---|
| FSEQ frame tb_toksim_fgu_seq (release frame exes, +BF_FRD_CHECK) | ffn.router, 4 frame classes 0L00-0L03, P129 / P130 | PASS, spans 857-865 (= S81-RTAG r160) |
| FSEQ | attn.wo_a, 0L00 / 0L01, P129 / P130 | PASS, spans 1764-1782 |
| FSEQ mutants | OT_BF6_MUT_ROH / OT_BF6_MUT_WSEL, router + wo_a, P130 | FAIL (PHASE_FAIL mismatches) |
| die-pair txn (tools/s81/bf6_front_n32_bench.py, QP_CHECK / QT_CHECK) | n32soq | PASS: 456 rows, 912 values, 448 configs, cycles 124422 |
| die-pair txn mutants | mroh / mwself | FAIL: DIFF TXN (fail witnesses bench/txn_mroh.log, bench/txn_mwself.log) |
| die-pair txn mutant | mwsel | not caught here (no multi-slice BF16 beat in this vector); it is caught by FSEQ |

Kit job benches must be n32soq / mroh / mwself, with those fail witnesses.
- The spec (physical/ref_tile_specs/s81_bf6_1020) is updated.
- The kit job.json is regenerated when the gate result is collected. job.json is not a gate input.
