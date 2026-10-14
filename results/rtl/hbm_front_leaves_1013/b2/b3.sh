#!/bin/bash
set -uo pipefail
v=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
files=(rtl/hbm_accel/generic/peers/ot_hgi_dma_front{,_core3b,_ctrl3b,_lane2,_xs,_xsw3b}.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hbm_accel/generic/peers/tb_hgi_dma_front_b2_epoch3.sv)
for m in 0 1 2; do
 "$v" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-CASEINCOMPLETE --top-module tb_hgi_dma_front_b2_epoch3 -GNL=8 -GXP=1 -GXQ=1 -GMUT=0 -GB2=1 -GMUT_B2=$m -Mdir b3obj$m "${files[@]}" -j 4 >b3build$m.log 2>&1 || exit 10
 set +e
 ./b3obj$m/Vtb_hgi_dma_front_b2_epoch3 +FULL >b3m$m.log 2>&1
 rc=$?
 set -e
 tail -8 b3m$m.log
 if [[ $m == 0 ]]; then [[ $rc == 0 ]] && grep -q 'PASS HGI_DMA_FRONT' b3m$m.log || exit 11; else [[ $rc != 0 ]] && grep -Eq 'FAIL|FATAL' b3m$m.log || exit 12; fi
 done
