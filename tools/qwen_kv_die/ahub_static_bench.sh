#!/bin/bash
set -euo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
MUT=${2:-0}
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
SRC='rtl/hdc/nearhbm/ot_qkd_ahub_static.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv rtl/hdc/nearhbm/ot_qkd_ahub_core.sv rtl/hdc/nearhbm/ot_nhb_tiles.sv rtl/hdc/nearhbm/ot_qkh_recip_leaf.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_pipe.sv'
"$V" --binary --timing --hierarchical -j "${JOBS:-4}" -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -GMUT="$MUT" --top-module tb_qkd_ahub_static -Mdir "$OUT/obj_$MUT" tools/qwen_composed_harness/lv6_hier/hier_attn.vlt rtl/test/qwen_kv_die/tb_qkd_ahub_static.sv $SRC > "$OUT/build_$MUT.log" 2>&1
"$OUT/obj_$MUT/Vtb_qkd_ahub_static" | tee "$OUT/run_$MUT.log"
