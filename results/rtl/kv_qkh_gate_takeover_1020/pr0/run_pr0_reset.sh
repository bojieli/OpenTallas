#!/bin/bash
set -eu
R=/srv/opentallas-scratch/claude/ref_gate/ot_qkh_ktree_lk_nc32c-20261020-041108/src
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
H=$R/rtl/hdc
"$V" --binary --timing --x-initial unique --x-assign unique -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DSYNTHESIS --top-module tb_pr0_reset -Mdir obj_reset \
 tb_pr0_reset.sv ot_rst_land_wrapper.v lane8_core_renamed.v \
 "$H/nearhbm/ot_qkh_subtiles.sv" "$H/nearhbm/ot_qwen_nearhbm_prod.sv" \
 "$R/rtl/lib/ot_rst_relay.sv" "$R/rtl/lib/ot_rst_relay_bounded32.sv" \
 "$H/ot_hdc_fp32_qkh_ncr.sv" "$H/ot_hdc_fp32_add_lat_nr.sv" "$H/ot_hdc_fp32_add_lat.sv" \
 "$H/ot_hdc_prefix.sv" "$H/ot_hdc_delay.sv" "$R/physical/ref_tile/ot_qkh_ktree_m5/src/rtl/hdc/ot_hdc_fastfp.sv" > build_reset.log 2>&1
for seed in 11 19;do
 ./obj_reset/Vtb_pr0_reset +verilator+seed+$seed +verilator+rand+reset+2 > reset_seed${seed}.log 2>&1
 grep '^PR0_RESET_PASS' reset_seed${seed}.log
done
