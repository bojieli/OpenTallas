#!/bin/bash
set -uo pipefail
v=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
p=rtl/hbm_accel/generic/peers
q=rtl/hbm_accel/generic/adapters/native_b2/su_quadrant
d=rtl/hbm_accel/generic/vm/b2
files=($p/ot_hgi_dma_front{,_core7b,_ctrl7b,_lane2,_xs_vm2,_xsw7b}.sv $p/ot_hgi_dma_ixpipe.sv $p/ot_hgi_dma_vm_{queue,router,transport}.sv rtl/lib/ot_rst_relay.sv $p/tb_hgi_dma_front_qwen_vm4_7b_latency.sv
$q/ot_hgi_su_ctlw_native_{q,lane2,h}.sv $q/ot_hbm_b2_{lane_cdc,su_vm4}.sv rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo_p2.sv
$d/ot_vms_{bank,hub,rstop,rcl,star,relay,slice}.sv rtl/link/ot_fifo_sram_fwft.sv
physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/*.v
physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/*.v
physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/*.v
physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/*.v)
m=${1:-0};phase=${2:-61};cap=${3:-16};idle=${4:-0}
"$v" --binary --timing -O2 -Wno-fatal --top-module tb_hgi_dma_front_qwen_vm4_7b_latency -GMUT=$m -GPHASE=$phase -GSOURCE_CAP=$cap -GREQ_IDLE=$idle -Mdir qvm7latencyobj${m}p${phase}c${cap}i${idle} "${files[@]}" -j 4 >qvm7latencybuild${m}p${phase}c${cap}i${idle}.log 2>&1 || { tail -30 qvm7latencybuild${m}p${phase}c${cap}i${idle}.log;exit 10; }
./qvm7latencyobj${m}p${phase}c${cap}i${idle}/Vtb_hgi_dma_front_qwen_vm4_7b_latency +FULL >qvm7latencym${m}p${phase}c${cap}i${idle}.log 2>&1;rc=$?;tail -12 qvm7latencym${m}p${phase}c${cap}i${idle}.log
if [[ $m == 0 ]];then [[ $rc == 0 ]] && grep -q 'PASS QWEN_VM4_LOAD' qvm7latencym${m}p${phase}c${cap}i${idle}.log || exit 11;else [[ $rc != 0 ]] && grep -Eq 'FATAL|FAIL' qvm7latencym${m}p${phase}c${cap}i${idle}.log || exit 12;fi
