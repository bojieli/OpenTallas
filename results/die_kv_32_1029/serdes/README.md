# DIE-KV-32 serdes remainder (10-29)

kv3_sys_SD / kv3_sys_SD_v1: native logical x6 PHY (`ot_qfd_serdes_112g_x6_phy`, W=522/521) placed and powered as its exact
fixed-W physical master. Pieces (all from Codex codex/kv-physical-prep-1027, narrow pick, no logic change):

- `tools/die_plan/specialize_serdes_phy.py` (+test, Codex 3b0005535): kit-only wire dispatcher; the kit's raw PHY becomes
  `g_native.u_macro` of `ot_qfd_serdes_112g_x6_phy_w52x` (BB + LEF + TT/FF lib), same 7-port ABI, 0 added cycles/state.
  Run on a fresh `bind.py kit-rtl` dir: `specialize_serdes_phy.py <kit_rtl_dir> results/kv_serdes_pg_event27`.
- `results/kv_serdes_pg_event27/` (Codex c49d5497f..9b66de546 views): modeled academic abstract; PG closure pending.
- gen_phys content `physical_inst`/`physical_master` (already on main 4bfd36986, from 7cf01a2dc).
- `apply_serdes_phys.py` + `serdes_phys_delta.json` (Codex dd4cdbbc7 sys_SD content + VDDPHY_SW/SE domains): fix-only plan
  delta; fails closed unless placement/outline/logical content match and each domain rect = content outline in die coords.
  CHECKED on intel1 die-kv-32-kits-1029/plan_band/die_plan.json -> serdes/die_plan_serdes.json: only kv3_sys_SD/_v1 and
  die.pg.domains change; rects SW [17.28,26060.4,1883.52,27032.4], SE [9192.96,26060.4,11059.2,27032.4] (sys_SE MY).

NOT done (next): kit-rtl for the two types -> specialize -> gen.py phys with the delta plan -> preflight, and the
post-synthesis check that the netlist instance is exactly `u_bound.u_core.u_phy.g_native.u_macro` (record says OWED).
