#!/bin/bash
# run inside ORFS image: lockstep r2c2(repair 0) vs r0c0_pc for the 3 shapes, normal + mutant
set -u; M=/w/physical/asap7_memory_macros_v2; cd /out
for s in "512 128 4" "64 512 1" "128 256 1"; do set -- $s; sh=${1}x${2}_m$3
  python3 -I /tb/gen_tb.py $1 $2 $3 20000 > tb_$sh.sv
  for mode in base MUT; do d=obj_${sh}_$mode; def=""; [ $mode = MUT ] && def="-DMUT"
    verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style $def --top-module tb --Mdir $d tb_$sh.sv $M/ot_sram_1r1w_${sh}_r2c2/ot_sram_1r1w_${sh}_r2c2.v $M/ot_sram_1r1w_${sh}_r0c0_pc/ot_sram_1r1w_${sh}_r0c0_pc.v > build_${sh}_$mode.log 2>&1 || { echo "BUILD FAIL $sh $mode"; tail -5 build_${sh}_$mode.log; continue; }
    echo "[$mode] $(./$d/Vtb | grep LOCKSTEP)"; rm -rf $d
  done
done
