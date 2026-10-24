#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -Wno-fatal +define+KVD_AKMUT=0 --top-module tb --Mdir obj ot_hdc_prefix.sv ot_hdc_fastfp.sv ot_hdc_delay.sv ot_hdc_fp32_add_lat.sv ot_hdc_fp32_add_lat_nr.sv qkd_astk_zn.sv qkd_astk_zn_head_p.sv qkd_astk_zn_r4.sv qkd_astk_zn_head_p_r4.sv tb.sv > build.log 2>&1
obj/Vtb | tee sim.log
