#!/bin/bash
set -uo pipefail
v=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in 0 1 2;do
 "$v" --binary --timing -O2 -Wno-fatal --top-module tb_hgi_dma_vm_transport9 -GMUT=$m -Mdir trans9obj$m rtl/hbm_accel/generic/peers/ot_hgi_dma_vm_{queue,router9,bank9,transport9}.sv rtl/hbm_accel/generic/peers/tb_hgi_dma_vm_transport9.sv -j 4 >trans9build$m.log 2>&1 || exit 10
 ./trans9obj$m/Vtb_hgi_dma_vm_transport9 >trans9m$m.log 2>&1;rc=$?;tail -8 trans9m$m.log
 if [[ $m == 0 ]];then [[ $rc == 0 ]] && grep -q 'PASS TRANSPORT' trans9m$m.log || exit 11;else [[ $rc != 0 ]] && grep -q 'FATAL TRANSPORT' trans9m$m.log || exit 12;fi
 done
