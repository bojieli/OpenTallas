# KV-BIND8 10-20: GEN9 strict-bind static tables (d11r replay) + tile RTL currency

Replay of the fixed `kv_static_params.py` on the UNCHANGED gen9d11r run (ep6 `qwen-kvsys/kvs14r-04b625135-gen9d11r`: case_kv/static_model.json,
relay_stages_netlist.json.gz digest ca253f59, fwd_lanes.json, port_bind_v2/die_bound.v): `static_params_d11r_b8.json`, `sp_d11r.log`.
Before: 74 FAILs (69 UNRESOLVED_STAGE, PLAN_PARAMS_STALE 151, BOOT_AGE_MISMATCH 14, PATH_STALE 32, AHUB_OFS_BOUND, PVFIN_PAIR_SKEW).
After: 2 FAILs, both real hardware gaps with owners:
- AHUB_OFS_BOUND: hub kit qkd_ahub_sdw hardened at AP_OFS {2,2,2,2} / FR_OFS 0; this table needs [-40,-40,-38,-39] / -7 (hub owner: re-harden at the
  table values, or boot-programmable offsets / fixed-table padding of ks_ahs, ap_*, ks_pvfst).
- ATTN_CALENDAR PVFIN_PAIR_SKEW 32/16 in 4096/8192 contexts: structural fix = pair END FLOOR control `rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tbf.sv`
  (both pairs end FEED / publish out_age on pair 0's issue count; 0 token cost since pvfin waits for max(P0,P1)=P0; no stall).
  Bench `tools/qwen_kv_die/pv_floor_bench.sh` (pair golden bit-exact, both pairs, FLOOR=1 skew 0 / FLOOR=0 shipping skew). Die integration
  (pvw _ba floor variant + ctl kit gate + compiler law P1 = P0) follows the bench PASS.

Tool fixes (all fail-closed paths kept):
1. Fork bids `X__fN` listed in relay_stages were looked up as bids of their own (no own net) -> resolved by the trunk's fork branch.
2. `pvh_*` source is the EXPANDED relay fork pvfork_*__u_r0: the table walks through it, so pvh is measured COMPOSITE from pvin_* on the
   V-header source ports (out_t/out_epoch/out_valid) -> header to pvw ctl, fork to the ASTK owner; e_after_header uses only their difference.
3. `hf__f0`: the health plane rewired kvs_attn.ufh (driver hp_fault_1349): age into the plane (34) + the plane leaf-latency bound (182).
4. Boot image is DATA (qkd_kv_die_cfg_a age words): re-emitted from the post-station table -> RUN/boot_ages.json (plan-image drift recorded).
5. PLAN_PARAMS_STALE / PATH_STALE are plan drift (no hardware consumer: the compiler takes the table params, hub / tile ages / boot image are
   checked on the table) -> info PLAN_PARAMS_DRIFT / PATH_DRIFT.
Tile RTL: `qkd_kvs_tiles_hroot_ff_k_mu_ba.sv` regenerated (sha 82693c8c, = Codex fresh-producer replay), `..._hs_mu_ba.sv` created (sha 6323c7df);
kvsys_prep.sh now refuses a missing / stale tile RTL for the run flags (`kv_static_die.py --check`, exit 8).
Open in the replay record: e_after_header differs between ports of one stack (WS 131/132, WN 107/109): compiler-consumed, recorded.
