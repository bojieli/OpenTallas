# N9: attention entry line credit kq (hgi-1010/g2 -> g3, 2026-10-11)

`hfd_attn_half_lo` returns one credit per PS row consumed on `kq[1:0] = {forwarded clock, v}` (`ot_attn_ks_credit`, rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv).
Bench: `physical/hbm_accel_die_views/svc/run_bench_ps_entry.sh` (the real PS svc SW segments; the entry credit RTL is the consumer of all 8 row ports; every stream credited; per-port accounting: credits never exceed landed rows and equal them at the end; credit-deadlock watchdog 8,192 cycles).
Source 81a0a111c (epyc3, iverilog). Verdict: sim_entry PASS (13,670 rows, 0 errors); OT_ATTN_MUT_KQ_DROP FAIL (credit stall); OT_ATTN_MUT_KQ_DUP FAIL (surplus credits). See summary.txt.
