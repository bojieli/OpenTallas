#!/usr/bin/env bash
set -euo pipefail
v=$(command -v verilator)
if [ -x /opt/verilator-5.050/bin/verilator ]; then v=/opt/verilator-5.050/bin/verilator; fi
"$v" --version
for mut in 0 1; do
 "$v" --binary --timing -Wno-fatal --top-module tb_escape -GMUT=$mut --Mdir obj_escape_$mut -o sim_escape rtl/test/sram_pin_access_1019/tb_escape.sv rtl/test/sram_pin_access_1019/escape_harness.sv physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v > build_$mut.log 2>&1
 set +e
 ./obj_escape_$mut/sim_escape > run_$mut.log 2>&1
 rc=$?
 set -e
 if [ "$mut" = 0 ]; then test "$rc" = 0; grep ESCAPE_COUPON_PASS run_$mut.log; else test "$rc" != 0; grep ESCAPE_MISMATCH run_$mut.log; fi
done
