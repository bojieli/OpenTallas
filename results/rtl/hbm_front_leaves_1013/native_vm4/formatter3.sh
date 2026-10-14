#!/bin/bash
set -uo pipefail
v=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in 0 1 8;do
 "$v" --binary --timing -O2 -Wno-fatal --top-module tb_hgi_dma_front_xs_vm3 -GMUT=$m -Mdir vm3obj$m rtl/hbm_accel/generic/peers/ot_hgi_dma_front_xs_vm3.sv rtl/hbm_accel/generic/peers/tb_hgi_dma_front_xs_vm3.sv -j 4 >vm3build$m.log 2>&1 || exit 10
 ./vm3obj$m/Vtb_hgi_dma_front_xs_vm3 >vm3m$m.log 2>&1; rc=$?
 tail -6 vm3m$m.log
 if [[ $m == 0 ]];then [[ $rc == 0 ]] && grep -q 'PASS XS_VM records=' vm3m$m.log || exit 11;else [[ $rc != 0 ]] && grep -q 'FATAL XS_VM errors=' vm3m$m.log || exit 12;fi
 done
