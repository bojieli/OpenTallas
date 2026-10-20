#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
D=results/rtl/kv_qkh_nc_safe32_1020
verilator --binary --timing --x-initial unique --x-assign unique -Wno-fatal -DSYNTHESIS --top-module tb_ncr_reset --Mdir ncr_reset_r6_build -j 4 "$D/tb_ncr_reset.sv" rtl/hdc/ot_hdc_fp32_qkh_ncr.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv physical/ref_tile/ot_qkh_ktree_m5/src/rtl/hdc/ot_hdc_fastfp.sv > ncr_reset_r6_build.log 2>&1
for seed in 20261020 173 905;do ./ncr_reset_r6_build/Vtb_ncr_reset +verilator+rand+reset+2 +verilator+seed+$seed >ncr_reset_$seed.log 2>&1;cat ncr_reset_$seed.log;done
