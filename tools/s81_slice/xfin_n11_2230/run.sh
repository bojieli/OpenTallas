#!/bin/bash
set -eu
O=${1:?output};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -DOT_S81DV_XFIN_N10 -DOT_S81DV_XFIN_N11 --top-module tb --Mdir "$O/obj" --build-jobs 4 rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv tools/s81_slice/xfin_n11_2230/reference.sv tools/s81_slice/xfin_n11_2230/tb.sv > "$O/build.log" 2>&1
"$O/obj/Vtb" > "$O/positive.log" 2>&1
cat "$O/positive.log"
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -DOT_S81DV_XFIN_N10 -DOT_S81DV_XFIN_N11 -DOT_S81DV_MUT_N11_MASK --top-module tb --Mdir "$O/mut_obj" --build-jobs 4 rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv tools/s81_slice/xfin_n11_2230/reference.sv tools/s81_slice/xfin_n11_2230/tb.sv > "$O/mut_build.log" 2>&1
set +e
"$O/mut_obj/Vtb" > "$O/mutant.log" 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ] && grep -q XFIN_N11_WRITE_MISMATCH "$O/mutant.log"
echo XFIN_N11_CAUSAL_MUTANT_CAUGHT
