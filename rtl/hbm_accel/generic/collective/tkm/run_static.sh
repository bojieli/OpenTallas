#!/bin/bash
set -euo pipefail
O=$(realpath -m "$1");VEC=$(realpath -m "$2");shift 2
mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic/collective
"$V" --binary --timing --hierarchical -j "${JOBS:-8}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --top-module tb_hgi_coll_tkm_static -Mdir "$O/obj" "$@" \
 "$C/p2p/qtkm_hier.vlt" "$C/tkm/tb_hgi_coll_tkm_static.sv" "$C/tkm/ot_hgi_coll_tkm_static.sv" "$C/tkm/ot_hgi_coll_tkm.sv" "$C/tkm/ot_hgi_coll_tkm_buffer.sv" rtl/lib/ot_rst_relay.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v >"$O/build.log" 2>&1
for c in syn_sel syn_cand edge_ties edge_zeros;do
 if [ -d "$VEC/$c" ];then "$O/obj/Vtb_hgi_coll_tkm_static" +DIR="$VEC/$c" >"$O/$c.log" 2>&1;fi
done
