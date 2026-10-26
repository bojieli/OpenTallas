# KV-FLOOR1 10-20: PV pair END FLOOR die integration (OT_KV_PVFIN_FLOOR=1, default off)

Evidence
- `pv_floor_bench_full_307565e07.log`: full floor sweep (ot-epyc7, KV-BIND8 bench `tools/qwen_kv_die/pv_floor_bench.sh`):
  FLOOR=1 bit-exact both pairs, out_age P0 == P1 at every context class incl 4097 / 8192; FLOOR=0 reproduces skew 32/16/0.
- kv_static_params replay on the UNCHANGED gen9d11r run (ep6 `qwen-kvsys/kvs14r-04b625135-gen9d11r`, same inputs as
  results/arch/kv_bind8_1020), source e4a3df4dc (`replay.sh`, `replay3.sh`):
  - `static_params_f0.json` flag off: FAIL AHUB_OFS_BOUND, RELAY_DOMAIN (129), ATTN_CALENDAR PVFIN_PAIR_SKEW (4096/8192, worst 32)
  - `static_params_f1.json` OT_KV_PVFIN_FLOOR=1, d11r netlist as built (ctl_tb): PVFIN_PAIR_SKEW gone (worst 0), new
    PVFIN_FLOOR_MISMATCH (compiler P1 = P0 but the die binds ot_qwen_tp8_pv_wide_ctl_tb) -- fail-closed as intended
  - `static_params_f1s.json` OT_KV_PVFIN_FLOOR=1 with die_bound.v's two pvw_*__u_ctl masters SUBSTITUTED ctl_tb ->
    ctl_tbf .END_FLOOR(1) (synthetic: same ports, table unchanged; stands for a floor GEN): FAIL AHUB_OFS_BOUND, RELAY_DOMAIN
    only. Full-record diff vs f0: only the PVFIN fields and the bound ctl master differ (every other result unchanged).
  - AHUB_OFS_BOUND / RELAY_DOMAIN are not floor items (hub kit offsets; relay clock domains) and are identical in all three.
- `unittest_f0.log` / `unittest_f1.log`: test_kv_static_programme + test_kv_pvw_padding 28/28 OK, flag off and on (ep6).
  Local: test_kv_bootage, test_kv_static_params, test_kv_pvw_padding, test_kv_pvw_residual_roles PASS (flag off and on).
