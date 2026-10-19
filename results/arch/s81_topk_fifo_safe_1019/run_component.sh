#!/bin/bash
set -euo pipefail
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$VL --version
for m in 0 1 2; do
 mkdir -p component_$m
 $VL --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -DMUT=$m --top-module tb_fifo results/arch/s81_topk_fifo_safe_1019/tb_fifo.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_queue_store.sv rtl/lib/ot_sram_showahead_1r1w.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v -Mdir "$PWD/component_$m/obj" >component_$m/build.log 2>&1
 set +e
 component_$m/obj/Vtb_fifo >component_$m/run.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then grep -q 'FIFO PASS' component_$m/run.log;else grep -q 'FIFO FAIL' component_$m/run.log;[ "$rc" != 0 ];fi
 tail -4 component_$m/run.log
 done
