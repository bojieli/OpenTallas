#!/bin/bash
# AD3-KV-RSHD 10-18: the PV pair result-stream bench (pv_rtrunk_bench.sh, Verilator 5.050) on the committed generated pair
# with its header leaf swapped to qkd_pv_rs_hd_f -- exactly what pv_trunk_gen --rs-hd f emits (rs_mods() changes only the
# header module name; ports / KV / wiring identical).  pv_rtrunk_bench_hdf.sh OUT [RS_MUT] [CTXS]  (from the repository root)
set -u
O=$1; mkdir -p "$O"
S=rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv
n=$(grep -c '^ qkd_pv_rs_hd_r #(.KV(32)) u_RH_r0 ' "$S")
[ "$n" = 1 ] || { echo "PV_PAIR_RS FAIL hdf: expected one qkd_pv_rs_hd_r header instance in $S, found $n"; exit 1; }
sed 's/^ qkd_pv_rs_hd_r #(.KV(32)) u_RH_r0 / qkd_pv_rs_hd_f #(.KV(32)) u_RH_r0 /' "$S" > "$O/qkd_pvw_die_t_hdf.sv"
grep -q '^ qkd_pv_rs_hd_f #(.KV(32)) u_RH_r0 ' "$O/qkd_pvw_die_t_hdf.sv" || { echo "PV_PAIR_RS FAIL hdf: swap failed"; exit 1; }
PVW="$O/qkd_pvw_die_t_hdf.sv" exec bash tools/qwen_kv_die/pv_rtrunk_bench.sh "$@"
