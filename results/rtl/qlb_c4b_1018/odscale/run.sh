#!/bin/bash
# QW-ODSCALE 10-19: od (o / down) DV stage with the compiler's station row scale (dv_lower_mat.station_row_scales:
# BTAB 1.0 for the AR matrices) on REAL L0 / L1 P8191 operands, bit-exact vs the TP8 ISA gold partials
# (fixtures L<n>_mat_od_tp8.npz = dv_layer_fixture.py tp8od) + regressions + mutant witnesses.
# Fresh tb_qfd_dv2 N12 build (Verilator 5.050) of this branch's sources (origin/main merged: MU_NU 1 default).
# usage: run.sh R (R = run root holding src/ and fx/)
R=$1; SRC=$R/src; FX=$R/fx
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
B=$R/runs/L0_od_tp8; mkdir -p $B
date -Is; echo BUILD obj_n12
( cd $SRC/rtl/test/qwen_dv && python3 -c "import sys; from pathlib import Path; sys.path.insert(0, '$SRC/tools/qwen_layerbench'); import dv_lower_bench as LB; LB.build(Path('$B'))" ) || { echo BUILD FAILED; tail -20 $B/build.log; exit 1; }
date -Is
python3 $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run od --fixture $FX/L0_mat_od_tp8.npz --work $B > $B/bench.out 2>&1
echo "rc=$?" >> $B/bench.out; echo "L0_od_tp8 $(head -1 $B/bench.out | cut -c1-200)"
[ -x $B/obj_n12/Vtb ] || { echo BUILD FAILED; tail -20 $B/build.log; exit 1; }
OBJ=$B/obj_n12
job() {  # name args...
  local name=$1; shift; local d=$R/runs/$name; mkdir -p $d; ln -sfn $OBJ $d/obj_n12
  python3 "$@" --work $d > $d/bench.out 2>&1; echo "rc=$?" >> $d/bench.out; echo "$name $(head -1 $d/bench.out | cut -c1-200)"
}
export -f job; export R SRC FX OBJ
{
echo "L1_od_tp8 $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run od --fixture $FX/L1_mat_od_tp8.npz"
echo "L0_od $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run od --fixture $FX/L0_mat_od.npz"
echo "L1_od $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run od --fixture $FX/L1_mat_od.npz"
echo "L0_qkv $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run qkv --fixture $FX/L0_mat_qkv.npz"
echo "L0_gu $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run gu --fixture $FX/L0_mat_gu.npz"
echo "MUT_L0_od_tp8_rawscale $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run od --mutant rawscale --fixture $FX/L0_mat_od_tp8.npz"
echo "MUT_L0_od_tp8_nostagger $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run od --mutant nostagger --fixture $FX/L0_mat_od_tp8.npz"
} | xargs -P 8 -L 1 bash -c 'job "$@"' _
