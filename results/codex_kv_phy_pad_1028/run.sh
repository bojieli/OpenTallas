#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd "$(dirname "$0")"
verilator --binary --timing -Wno-fatal -j 4 --top-module tb_qkd_host_rx_pad5 -Mdir obj_nom ../../rtl/qwen_sys/host_20261013/qkd_host_rx_pad5.sv reference.sv tb_lockstep.sv > build_nom.log 2>&1
./obj_nom/Vtb_qkd_host_rx_pad5 > nominal.log 2>&1
verilator --binary --timing -Wno-fatal -j 4 --top-module tb_qkd_host_rx_pad5 -GMUT=1 -Mdir obj_mut ../../rtl/qwen_sys/host_20261013/qkd_host_rx_pad5.sv reference.sv tb_lockstep.sv > build_mut.log 2>&1
set +e
./obj_mut/Vtb_qkd_host_rx_pad5 > mutant.log 2>&1
rc=$?
set -e
if test "$rc" = 0;then echo 'FAIL mutant survived';exit 1;fi
if ! grep -q 'lockstep data' mutant.log;then cat mutant.log;exit 1;fi
echo 'PASS nominal lockstep and MUT=1 caught'
