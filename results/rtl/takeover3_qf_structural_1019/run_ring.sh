#!/bin/bash
set -eu
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in 0 1 2; do
 mkdir -p ring$m
 /usr/bin/time -v -o ring$m/build.time "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -DOT_MEM_NO_INIT --top-module tb_s81sl_cap_phase_ring -GMUT=$m -Mdir ring$m/obj rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_phase.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_cap_phase_ring.sv --build-jobs 4 >ring$m/build.log 2>&1
 set +e
 ring$m/obj/Vtb_s81sl_cap_phase_ring >ring$m/run.log 2>&1
 rc=$?
 set -e
 echo "$rc" >ring$m/exit.txt
 if [ "$m" = 0 ] && [ "$rc" != 0 ]; then exit 1;fi
 if [ "$m" != 0 ] && [ "$rc" = 0 ]; then exit 1;fi
 done
