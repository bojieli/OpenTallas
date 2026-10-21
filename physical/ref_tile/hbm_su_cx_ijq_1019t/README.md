# hbm_su_cx_ijq_1019t -- ij_q SAFE_GATHER successor + split landed reset (LEAD2-HBM/L2H-SU, 10-19)

1019t = 1019s (gate WARN 08f64ff5f, 0 fail) + reset distribution: the 2-stage face landing replicates its last stage x3
(reset_landing copies rst_q_n=3 -> OT_RST_LAND_COPIES) and ot_rst_copies re-points the 86 landed async reset loads over
the copies, <= 32 each (reset_relay_split max 32). Same RTL, outline, pins and clock as 1019s.

Predecessor: hbm_su_cx_ijq_1018w route rw-136f736ca NEEDS_RTL (TT -73.23 / FF +25.2 / DRC 0; ioh[13] -> ob0[99], 77 D pins).
RTL: ot_hbm_su_static_cxport_ij_q SAFE_GATHER=1 (claude/lhsu-cxijq-1019; d8afaa78e factored gather + LH-SU r3 control/fanout fix).
Evidence: results/rtl/cxijq_safe_1019/r3/ (Verilator 5.050 SD0/SD2 PASS, mutants 4/5/6 FAIL; all-module Yosys census).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS. Every output is a register (ob0/ob1 banks, fault); jb -> ring register after one 2:1 mux; inj_q -> one AND-OR level -> pq
  partial registers (replace the old iq capture flops on the same edge). Reset lands in 2 registered stages at the N face (reset_landing.json).
2 Reach: PASS. Outline 216 x 388.8; textbook reach on w 193 um < 405; each pq gathers 4 bits of ONE input port (~47 um apart).
3 Fanout: FIXED. r2 census had ctl_v 63-64, shared ohdec adder carries 126-131, rp[0] 65. Now 8 kept COPY_ID paramods (each registers its own
  20b control and decodes locally; 512 onehot flops survive, each bit 32 loads), 65 kept bank-select copies (<= 33 loads). Every non-clock,
  non-reset net <= 33 loads (census r3/fanout_all.json). Landed reset: 1019t splits the 86 async loads over 3 kept landing copies (<= 32 each; gate checks ot_rst_copies.tsv).
  The 65 bank-select copies at 33 loads = 32 data-mux selects + the copy's own toggle (rp <= ~rp): within the ~32 rule, waived with that reason.
4 Depth: FIXED. Gather = 4:1 AND-OR into pq, then 4:1 OR into ob (was 16:1 behind a 256-load select in one cycle). Control ring: one-hot
  4-6:1 AND-OR read into per-copy registers; decode = 2 equality compares + AND.
5 Storage: PASS. Control delay is a circular ring of D=4+SD 20b words (80-120 b, no long flop chain); data banks are the existing seam banks.
6 Floorplan: WAIVED-with-reason (util). No macros. Pin-bound outline: 6,150 signal bits need >= 1,025 um of face at 6 pins/um; 216 x 388.8
  (perimeter 1,209 um) is the ij_s/ij_q seam pair slot (324 x 388.8, H-D4G) -> util ~5%, aspect 1.8:1. Full std-cell band, no islands.
7 Clock: PASS on w (unclustered CTS TT/FF pin-flop spread 33.9/33.2 ps, single root clk_q); io_hold_margin 0.03.
8 Schedule: PASS. 0 added edges (registered per-copy control reads the ring one slot ahead); latency and 3:4 seam calendar unchanged.

Not done here (needs ij_s + die seam re-grant): ob0/ob1 bit interleave on the E face (182 um bank-copy separation, within reach).
