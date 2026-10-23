#!/bin/bash
# BINDER2 10-23: KV v3.4 bind inputs on top of KV-P3b's bind/asbuilt.json (claude/kv-p3b-1023 @43d7dc926).
# 1. source tree = git archive e33504a6f (rtl tools results/arch/*kv* physical/ref_tile spec+views physical/qkd_astk_strip/macros
#    qwen_missing_phy serdes bb) + claude/kv-p3-rtl-1023 @8d7467e8a rtl/qwen_sys/kv_plan_leaves_1023 + rtl/lib/ot_dp_{id,efault}.sv
#    + plan claude/kv-p3b @3845962a2 physical/die_plan/qwen_kvsys (v3.4)
# 2. as-built netlist = the rtl6 GEN die.v (sha e1fc838f) bound by kv_bound_netlist.py with the rtl6 kv_flags.env + expand.json
#    (GEN bundle-wrapper masters -> RTL modules on the same die bits):
#      (set -a; . kv_flags.env; unset OT_KV_FAIL_JSON; python3 tools/qwen_kv_die/kv_bound_netlist.py die.v --expanded expand.json --out-dir KVB)
# 3. asbuilt_binder2.json = asbuilt.json + netlist KVB/die_bound.v, prefer = bound_netlist.json master files, files += KVB hard
#    models + ASAP7 stdcell verilog (ORFS asap7 platform, gate-level grp_r2c leaves), rst_region transport regex,
#    substitute_inst (class-C chain heads + ep_s_e), map_file with [partition, canonical local name] from stage1_v33 'where',
#    plan_cells = bind/plan_cell_conns_v34.json (KV-P4 claude/kv-p4-1023 @1cb50b545: ID lanes, ot_dp_efault, u_fch, hub_C tree),
#    lint_split (one Verilator run per partition module; the whole die in one run is OOM at 128 GB),
#    rewires = bind/plan_rewires_v34.json (KV-P4 @a73f158f5) classes astk_ectl_relabel + hsl_S_orientation with
#      port_map/port_names = KVB/bound_netlist.json (die port -> RTL port); hsl chain-end variant on hsl_*_0 in all quads,
#    reset_spines host.(die_rst_n|hbm_rst_n|host_rst_n) (clocks_v32 reset_root), pll keep_leaf (hub_C content),
#    map asbuilt_map_binder2.json (+ serdes shim AND glue -> hub_Wi).
# 4. python3 tools/die_plan/bind.py all physical/die_plan/qwen_kvsys/die_plan.json --asbuilt asbuilt_binder2.json --out OUT
