#!/bin/bash
# QW-REALSTG 10-19: DV stage benches on REAL L0 / L1 operands at P8191 (fixtures: tools/qwen_layerbench/dv_layer_fixture.py),
# reusing the completed tb_qfd_dv2 N12 Verilator 5.050 executable (QW-CLAYER reg_vec obj_n12, symlinked, never modified).
# usage: run.sh R (R = run root holding src/ and fx/)
R=$1; SRC=$R/src; FX=$R/fx; OBJ=/srv/opentallas-scratch/claude/qw-clayer-1018/runs/reg_vec/work/obj_n12
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
job() {  # name kind args...
  local name=$1; shift; local d=$R/runs/$name; mkdir -p $d; ln -sfn $OBJ $d/obj_n12
  python3 "$@" --work $d > $d/bench.out 2>&1; echo "rc=$?" >> $d/bench.out; echo "$name $(head -1 $d/bench.out | cut -c1-200)"
}
export -f job; export R SRC FX OBJ
{
for L in 0 1; do
  echo "L${L}_resid1 $SRC/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode resid --fixture $FX/L${L}_resid1.npz"
  echo "L${L}_resid2 $SRC/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode resid --fixture $FX/L${L}_resid2.npz"
  echo "L${L}_qk $SRC/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode qk --fixture $FX/L${L}_qk.npz"
  echo "L${L}_silu $SRC/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode silu --fixture $FX/L${L}_silu.npz"
  echo "L${L}_qkv $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run qkv --fixture $FX/L${L}_mat_qkv.npz"
  echo "L${L}_gu $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run gu --fixture $FX/L${L}_mat_gu.npz"
  echo "L${L}_od $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run od --fixture $FX/L${L}_mat_od.npz"
done
echo "MUT_L0_resid1_arwin $SRC/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode resid --mutant arwin --fixture $FX/L0_resid1.npz"
echo "MUT_L0_qk_ropesign $SRC/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode qk --mutant ropesign --fixture $FX/L0_qk.npz"
echo "MUT_L0_silu_nor $SRC/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode silu --mutant nor --fixture $FX/L0_silu.npz"
echo "MUT_L0_qkv_sbase1 $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run qkv --mutant sbase1 --fixture $FX/L0_mat_qkv.npz"
echo "MUT_L0_gu_sbase1 $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run gu --mutant sbase1 --fixture $FX/L0_mat_gu.npz"
echo "MUT_L0_od_nostagger $SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py --run od --mutant nostagger --fixture $FX/L0_mat_od.npz"
} | xargs -P 10 -L 1 bash -c 'job "$@"' _
verilator --version
