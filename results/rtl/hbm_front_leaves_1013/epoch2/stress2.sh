#!/bin/bash
set -uo pipefail
v=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
files=(rtl/hbm_accel/generic/peers/ot_hgi_dma_front{,_core2,_ctrl2,_lane2,_xs,_xsw2}.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hbm_accel/generic/peers/tb_hgi_dma_front_epoch2.sv)
for m in 0 1; do
 "$v" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-CASEINCOMPLETE --top-module tb_hgi_dma_front_epoch2 -GNL=2 -GXP=1 -GXQ=1 -GXS=1 -GMUT=$m -Mdir stress2obj$m "${files[@]}" -j 4 >stress2build$m.log 2>&1 || exit 10
 set +e
 ./stress2obj$m/Vtb_hgi_dma_front_epoch2 >stress2m$m.log 2>&1
 rc=$?
 set -e
 tail -8 stress2m$m.log
 if [[ $m == 0 ]]; then [[ $rc == 0 ]] && grep -q 'PASS HGI_DMA_FRONT' stress2m$m.log || exit 11; else [[ $rc != 0 ]] && grep -Eq 'FAIL|FATAL' stress2m$m.log || exit 12; fi
 done
