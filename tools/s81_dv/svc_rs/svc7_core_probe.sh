#!/usr/bin/env bash
set -euo pipefail
G=$(cd "${1:?graph directory}" && pwd)
O=$G/${2:-core_probe}
MODE=${3:-base}
DEFINES=()
if [ "$MODE" = dq ];then DEFINES=(-DSVC7_CORE_MUT_DQ);elif [ "$MODE" != base ];then exit 2;fi
mkdir -p "$O"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --binary --timing --x-initial unique -j 4 -Wno-fatal -Wno-WIDTH -DOT_MEM_NO_INIT "${DEFINES[@]}" --top-module tb_svc7_chunk_core -Mdir "$O/obj" -o sim "$G/native.v" "$G/verify_canonical/formal_prep/library_model_formal.v" rtl/hdc/v41x/ot_s81svc7_bmul_native.v rtl/hdc/v41x/ot_s81svc7_bmul_graph_input.sv rtl/hdc/v41x/ot_s81svc7_chunk_core.sv rtl/hdc/v41x/ot_s81svc7_chunk_reduce.sv rtl/hdc/v41x/ot_s81svc7_skew_sram.sv rtl/hdc/v41x/ot_s81svc7_add_graph_input.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv tools/s81_dv/svc_rs/tb_svc7_chunk_core.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v > "$O/build.log" 2>&1
for s in 3 17;do "$O/obj/sim" +verilator+rand+reset+2 +verilator+seed+$s > "$O/run_s$s.log" 2>&1;tail -n 5 "$O/run_s$s.log";done
