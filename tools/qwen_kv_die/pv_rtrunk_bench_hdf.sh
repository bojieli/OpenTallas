#!/bin/bash
# AD3-KV-RSHD 10-18: the PV pair result-stream bench (pv_rtrunk_bench.sh, Verilator 5.050) on the committed generated pair
# with its header leaf swapped to qkd_pv_rs_hd_f -- exactly what pv_trunk_gen --rs-hd f emits (rs_mods() changes only the
# header module name; ports / KV / wiring identical).  pv_rtrunk_bench_hdf.sh OUT [RS_MUT] [CTXS]  (from the repository root)
set -u
O=$1; mkdir -p "$O"
S=rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv
# HKV-PVRS3 10-19: f2 native PASS -> pv_trunk_gen default --rs-hd f; the committed netlist already binds qkd_pv_rs_hd_f at
# RS_D 50, so bench it as committed (the r -> f swap below is kept only for an r netlist).
if grep -q '^ qkd_pv_rs_hd_f #(.KV(32)) u_RH_r0 ' "$S"; then exec bash tools/qwen_kv_die/pv_rtrunk_bench.sh "$@"; fi
n=$(grep -c '^ qkd_pv_rs_hd_r #(.KV(32)) u_RH_r0 ' "$S")
[ "$n" = 1 ] || { echo "PV_PAIR_RS FAIL hdf: expected one qkd_pv_rs_hd_r header instance in $S, found $n"; exit 1; }
# HKV-PVRS2 10-19: qkd_pv_rs_hd_f rev f2 registers every input at its pin -> header 2 edges, pv_trunk_gen --rs-hd f emits
# RS_D + 1 (diff-checked: the --no-place --rs-hd f netlist differs from the committed r netlist in exactly these two lines).
# env HDF_RS_D_ADJ (default 1) = the RS_D increment; 0 = negative control (the f1 one-stage calendar -> every beat late, FAIL).
A=${HDF_RS_D_ADJ:-1}
sed 's/^ qkd_pv_rs_hd_r #(.KV(32)) u_RH_r0 / qkd_pv_rs_hd_f #(.KV(32)) u_RH_r0 /' "$S" \
 | perl -pe 's/^( localparam integer RS_D=)(\d+);/$1.($2+'"$A"').";"/e' > "$O/qkd_pvw_die_t_hdf.sv"
grep -q '^ qkd_pv_rs_hd_f #(.KV(32)) u_RH_r0 ' "$O/qkd_pvw_die_t_hdf.sv" || { echo "PV_PAIR_RS FAIL hdf: swap failed"; exit 1; }
d0=$(grep -oP '^ localparam integer RS_D=\K\d+' "$S"); d1=$(grep -oP '^ localparam integer RS_D=\K\d+' "$O/qkd_pvw_die_t_hdf.sv")
[ -n "$d0" ] && [ "$d1" = $((d0 + A)) ] || { echo "PV_PAIR_RS FAIL hdf: RS_D $d0 -> $d1 (want +$A)"; exit 1; }
PVW="$O/qkd_pvw_die_t_hdf.sv" exec bash tools/qwen_kv_die/pv_rtrunk_bench.sh "$@"
