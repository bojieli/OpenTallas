# Current paired Qwen/KV seam: complete calendar boot receipt

Original failing vehicle: `codex/qw-xdie-receipt-2215` commit `702d24a78`, immutable `results/rtl/xdie_qwen_1018/cur_r1/` (40 verified source snapshots). Original current K_REAL4 cases FAIL798: first KV D2D end fault at cycle183/relative1, then KV record fault816 and native59 RX-time fault2595. Historical K_REAL3 PASS is a different vehicle.

The bound `qkd_d2d_static_sfm` uses `FEG=1`. Its `ot_qwen_d2d_cal_sfg` authorizes start only after every entry and segment-base register have been written. The original vehicle loads addresses0..31 but never the base register at address32. This is a testbench boot protocol omission; the first-epoch guard must remain enabled. The base receipt is required even with cal_seg0.

Repair: widen bench config address to6bits, use6bit loop casts, connect the full address to both die masters, and explicitly write segment-base0 at address32 before host boot/calendar start. No production RTL change is introduced by this repair. `XQ_SKIP_BASE=1` restores the omitted-base causal negative. Diagnostics print the exact FEG receipt on first end fault.

`diag6` is actual current paired one-layer PASS using Verilator5.050: native59, K_REAL4 r17 attention plus real pvfin, SFM SRAM link with FEG1, PHY5, seam C2,2,2,3,2,2/K11,11,9,9,9,9,9 and TXDP C8/3/1/10 K22/4/3/3. C2K CMD32, Q31 33; K2C RESULT31 31; KVN20; roundtrip1842; KV service1779; status27; compute completion219 after last RESULT. These are measured cycles, not a full die simulation.

`diag4`/`diag5` preserve a failed intermediate setup edit: widening cfg_a while retaining signed5bit loop casts sign-extended entries16..31 to addresses48..63. Trace shows pin16 became48 and seen0000ffff/base1. Corrected6bit casts restore all32 writes. These intermediate failures are not the original design failure and are not passes.

Qualification limit: the positive vehicle compiles a corrected r17 TX_SHIFT1/STATUS_DELAY213 paired calendar, not the images currently bound by both dies. Exact bound-image and compute codec1 mismatches are causal-negative cases. K22 image expects seam11/9/9; current KV d23p3 natural tx_record13 exceeds image9, so geometry remains blocked independently. No stage contract has been relaxed, and no die closure is asserted.

Source overlay in this branch copies the exact original40snapshot sources; inherited uncommitted lane preparation relative to branch HEAD comprises current-case runner, K_REAL4 bench, compiler r17 timing options, and removal of an already duplicated native59 declaration. These are prerequisites from the immutable original, not new repair production logic. See source.sha256 for each run.

## Completed proof

`proof1`: fleet ot-epyc6 unit `oth-ubuntu-47930-1792560172`, terminal exit0. Four positives (`cur_pair`, `cur_pair_l0`, `cur_pair_phy9`, `cur_pair_t8192`) each PASS35layers, bit-exact32Q/32RESULT/4KVN and STATUS/completion on compiled cycles. Nine negatives all fail: missing base, bound image, codec1 computeRX, C TXDP+1, late KV run, torn KV RX, missing STATUS done bit, RESULT bit flip and PHY bit flip. Omitted-base witness has seenffffffff/base0 and faults on first start. Every source hash in proof1/source.sha256 matches the final working source. Against immutable original702d24a78,38/40sources remain byte-identical; only bench and runner differ.

PHY5: CMD32/Q3133, RESULT31, KVN20, roundtrip1842, status27, completion219 afterRESULT31. PHY9 adds4 per leg: CMD36/Q3137, RESULT35, KVN24, roundtrip1850, status31; completion remains219. L0 and T8192 match PHY5 static exchange ages. The compiler extension X is8 for normal layers,16 forPHY9 and-214 forL0; preserve those values and the213cycle status tail in composition.
