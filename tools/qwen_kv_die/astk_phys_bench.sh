#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$1"
D=(); if [ "${2:-0}" = 1 ]; then D=(-DKVD_ASTK_RLY_MUT); fi
iverilog -g2012 "${D[@]}" -s tb_qkd_astk_phys -o "$1/tb" "$R/rtl/test/qwen_kv_die/tb_qkd_astk_phys.sv" "$R/rtl/qwen_sys/split_20261014/qkd_astk_phys.sv" "$R/rtl/hdc/ot_hdc_delay.sv"
vvp "$1/tb"
