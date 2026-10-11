# IDX exactness-audit fixes (hgi-1010/g, 2026-10-10)

1. `ot_hgi_idx_index.sv` (used by the die view hfd_hgi_idx): the top-k / candidate output FIFOs (8 entries, 3-bit
   pointers) tested empty as `tft != tfh`, so a full FIFO looked empty.  Now the `_native` fix: occupancy counters
   tfn / cfn (pop / push accounting, ninth beat refused as a fault).  MUT 3 = the historical pointer test.
   Gate `rtl/test/hbm_accel/tb_hgi_idx_native_output_fifo.sv` (iverilog 12): native PASS; legacy (fixed) PASS
   "drain eight full credited beats"; legacy OVERFLOW PASS "refused ninth beat"; legacy MUT 3 **FAILS** (full eight-beat
   FIFO failed to drain).
2. `tb_hgi_idx_unit.sv`: the VM model queued only one request (a second was silently ignored).  Now up to 4 in flight,
   in order, random latency (a fifth is a bench fatal).  CF-TOPK (9 vectors, Verilator 5.050, ot-epyc3,
   `tools/hgi_unit_tput/run_idx_unit_cf.sh`): PREF 0 PASS (max 1 outstanding), PREF 1 PASS (max 4 outstanding);
   MUT 1 FAILS on both.
