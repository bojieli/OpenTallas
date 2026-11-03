#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
iverilog -g2012 -s ot_hnx_sfu_store_a_regional4_captured -tnull ot_hnx_sfu_store_a_regional4_captured.sv ot_hgi_sfu_store_a_regional_capture.sv ot_hnx_sfu_store_a_regional4.sv ot_hgi_su_lgroup2_regional_write.sv ot_hgi_su_lbank.sv ot_sram_1r1w_256x256_m2_r2c2_bb.v > elaborate.log 2>&1
iverilog -g2012 -s ot_hgi_sfu_ctl_storeA_regional_export -tnull ot_hgi_sfu_ctl_storeA_regional_export.sv > elaborate_CTL.log 2>&1
echo 'PASS actual 32-native-SRAM regional4 source elaboration'
