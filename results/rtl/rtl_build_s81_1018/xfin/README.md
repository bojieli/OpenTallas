# xfin ENG mode (RTL-BUILD-S81 item 2b, 10-18) -- source 269ef81a1, Verilator 5.050 on ot-epyc4

- RTL: `rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv` (ot_s81dv_xfin `mode`, `e_v/e_c/e_hh/e_kk/e_dd`; ot_s81dv_eng_finish; ot_s81dv_xstop `eng/ej_*` slot-fill inject).
- Bench `tools/s81_dv/xfin_eng_bench.sh` -> `tb_s81dv_xfin16e`: 16 xfin on the snake ring (LS 9 / LE 29), golden
  `tools/s81_dv/xfin_eng_golden.py` (hdc_golden_v41 chunk8 csum of h*h, k*k, (h*w)*k over D 5120, 4 copies, signed zeros), two go's.
  - PASS ORD 0 (leaf-major) GAP 0 seed 1: 128 results bit exact, go -> last e_v 526 cyc, last partial -> last e_v 464 cyc (`eng_base_ord0_gap0_seed1.log`).
  - PASS ORD 1 (vector-major) GAP 2 seed 7: go -> last 542, last partial -> last 362 (`eng_base_ord1_gap2_seed7.log`).
  - MUT_ETAG (slice 3 swaps vector tags 1/5): FAIL err=32 (`mutetag.log`). MUT_EASSOC (heap nodes 4/5 re-associated): FAIL err=128 (`muteassoc.log`).
- NORM regression `norm16_bench.sh base xfin`: PASS, rstd 3fbf858b, last partial -> first rstd 234, spread 13 = the closed x5 numbers (`norm_regression.log`).
- Latency vs the S81U-MIX estimate (exchange 111 + finish 270 = 381 after the reduce): measured 464 after the last partial (GAP 0);
  the 12 flits/slice share the ring with forwards (slot fill) and each copy adder runs 3 x 79 adds. Speed-up if needed: 2 adders per copy.
- Area: 4 x 3 trees x (80 leaves + 79 nodes) x 32 b ~ 61k flops: the tile grows (std area est. 60000 um2, remote gate measures).
