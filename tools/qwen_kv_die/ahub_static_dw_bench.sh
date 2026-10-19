#!/bin/bash
# ahub_static_dw_bench.sh OUT [MUT=0]: the KV die hub element qkd_ahub_static_dw (static six-root hub + reciprocal export
# to pvfin.fr) between the actual attention root and the actual qkd_pv_fin_s, with die relays (tb_qkd_ahub_static_dw).
# One AHUB_DW line; exit 0 only on PASS (mutants 1-3 expect FAIL).  Run from the repository root (fleet, via ot-run).
set -u
O=$1; M=${2:-0}
mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv
rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_pipe.sv
rtl/hdc/nearhbm/ot_qkd_ahub_static_cal_gen.sv rtl/hdc/nearhbm/ot_qkd_ahub_core.sv rtl/hdc/nearhbm/ot_nhb_tiles.sv
rtl/hdc/nearhbm/ot_qkh_recip_leaf.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv rtl/hdc/nearhbm/qkd_ahub_static_dw.sv
rtl/qwen_sys/split_20261014/qkd_attn_service_root.sv rtl/qwen_sys/split_20261014/qkd_pv_fin_s.sv
rtl/test/qwen_kv_die/tb_qkd_ahub_static_dw.sv"
sha256sum $SRC "$0" > "$O/source_m$M.sha256"
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 4 \
  --top-module tb_qkd_ahub_static_dw -GMUT=$M --Mdir "$O/obj_m$M" $SRC > "$O/build_m$M.log" 2>&1 \
  || { echo "AHUB_DW FAIL build"; grep -m8 '%Error' "$O/build_m$M.log"; exit 1; }
"$O/obj_m$M/Vtb_qkd_ahub_static_dw" > "$O/run_m$M.log" 2>&1
grep -E '^AHUB_DW FAIL mut=[0-9]+ first' "$O/run_m$M.log" | head -2
line=$(grep -E '^AHUB_DW (PASS|FAIL mut=[0-9]+ errors)' "$O/run_m$M.log" | tail -1)
echo "${line:-AHUB_DW FAIL no verdict line}"
case "$line" in "AHUB_DW PASS"*) exit 0;; *) exit 1;; esac
