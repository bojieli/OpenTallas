#!/bin/bash
# TOKSIM-QW/STG 10-19: DV compute-die stage benches on the RELEASE RTL (origin/claude/qw-gen3-1019 @221cf90b7) with the
# QW-REALSTG real L0/L1 operands at P8191 (fixtures from QW-REALSTG fx/, tools/qwen_layerbench/dv_layer_fixture.py).
# usage: run.sh R CFG   (R = run root holding src/ and fx/; CFG = base | rel)
#   base: tb_qfd_dv2 N12 default parameters (MU_NU 1, SU_LT 0) = the QW-REALSTG configuration on gen3 RTL
#   rel : the release slice kit parameters (physical/ref_tile/qfd_dv_slice2_{w,e} kit.env: SU_LT 1, MU_NU 4)
R=$1; CFG=$2; SRC=$R/src; FX=$R/fx; W=$R/$CFG
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
[ "$CFG" = rel ] && export DV_LOWER_VFLAGS='-GMU_NU=4 -GSU_LT=1'
mkdir -p $W/build $W/cal_mat $W/runs; verilator --version > $W/verilator.txt
VB=$SRC/rtl/test/qwen_dv/dv_lower_vec_bench.py; MB=$SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py
t0=$(date +%s)
python3 $SRC/rtl/test/qwen_dv/dv_lower_bench.py --work $W/build --calibrate > $W/build/slice_calibrate.out 2>&1; echo "rc=$?" >> $W/build/slice_calibrate.out
python3 $VB --work $W/build --mode calibrate > $W/build/calibrate.out 2>&1; echo "rc=$?" >> $W/build/calibrate.out
echo "build+vec calibrate $(( $(date +%s) - t0 )) s" > $W/timing.txt
[ -x $W/build/obj_n12/Vtb ] || { echo BUILD FAILED; tail -30 $W/build/build.log; exit 2; }
ln -sfn $W/build/obj_n12 $W/cal_mat/obj_n12
python3 $MB --work $W/cal_mat --calibrate > $W/cal_mat/calibrate.out 2>&1; echo "rc=$?" >> $W/cal_mat/calibrate.out
VA=$W/build/vec_ages.json; SA=$W/cal_mat/stn_ages.json
job() {
  local name=$1; shift; local d=$W/runs/$name; mkdir -p $d; ln -sfn $W/build/obj_n12 $d/obj_n12
  python3 "$@" --work $d > $d/bench.out 2>&1; echo "rc=$?" >> $d/bench.out; echo "$name $(head -1 $d/bench.out | cut -c1-200)"
}
export -f job; export W
{
for L in 0 1; do
  for m in resid1:resid resid2:resid qk:qk silu:silu; do n=${m%%:*}; md=${m##*:}
    echo "L${L}_$n $VB --mode $md --ages $VA --fixture $FX/L${L}_$n.npz"; done
  for r in qkv gu od; do echo "L${L}_$r $MB --run $r --ages $SA --fixture $FX/L${L}_mat_$r.npz"; done
done
echo "lm $MB --run lm --ages $SA"
echo "emb $MB --run emb --ages $SA"
echo "MUT_L0_resid1_arwin $VB --mode resid --mutant arwin --ages $VA --fixture $FX/L0_resid1.npz"
echo "MUT_L0_qk_ropesign $VB --mode qk --mutant ropesign --ages $VA --fixture $FX/L0_qk.npz"
echo "MUT_L0_silu_nor $VB --mode silu --mutant nor --ages $VA --fixture $FX/L0_silu.npz"
echo "MUT_L0_qkv_sbase1 $MB --run qkv --mutant sbase1 --ages $SA --fixture $FX/L0_mat_qkv.npz"
echo "MUT_L0_gu_sbase1 $MB --run gu --mutant sbase1 --ages $SA --fixture $FX/L0_mat_gu.npz"
echo "MUT_L0_od_nostagger $MB --run od --mutant nostagger --ages $SA --fixture $FX/L0_mat_od.npz"
echo "MUT_lm_amax_local $MB --run lm --mutant amax_local --ages $SA"
echo "MUT_emb_emb_late $MB --run emb --mutant emb_late --ages $SA"
} | xargs -P 12 -L 1 bash -c 'job "$@"' _
echo "total $(( $(date +%s) - t0 )) s" >> $W/timing.txt
