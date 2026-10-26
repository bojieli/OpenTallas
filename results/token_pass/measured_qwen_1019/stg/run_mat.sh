#!/bin/bash
# TOKSIM-QW/STG 10-19 21:40: matrix-side rerun. run.sh's mat calibrate died (gen3 dv_lower.cmd_stn makes kc mandatory,
# the realstg dv_lower_mat lowering did not pass it), so every mat stage / lm / emb / mat mutant ERRORed (no stn_ages).
# Fix: KC = 1 in dv_lower_mat + kc=1 in the bench calibrate (the bench drives one final block per (round, j); field 0 =
# the realstg encoding). Reuses run.sh's obj_n12 build of the same cfg (same Verilator, same params).
# usage: run_mat.sh R CFG
R=$1; CFG=$2; SRC=$R/src; FX=$R/fx; W=$R/$CFG
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
[ "$CFG" = rel ] && export DV_LOWER_VFLAGS='-GMU_NU=4 -GSU_LT=1'
[ -x $W/build/obj_n12/Vtb ] || { echo NO BUILD; exit 2; }
MB=$SRC/rtl/test/qwen_dv/dv_lower_mat_bench.py; t0=$(date +%s)
python3 $MB --work $W/cal_mat --calibrate > $W/cal_mat/calibrate.out 2>&1; echo "rc=$?" >> $W/cal_mat/calibrate.out
SA=$W/cal_mat/stn_ages.json; [ -f $SA ] || { echo MAT CALIBRATE FAILED; tail -20 $W/cal_mat/calibrate.out; exit 3; }
job() {
  local name=$1; shift; local d=$W/runs/$name; mkdir -p $d; ln -sfn $W/build/obj_n12 $d/obj_n12
  python3 "$@" --work $d > $d/bench.out 2>&1; echo "rc=$?" >> $d/bench.out; echo "$name $(head -1 $d/bench.out | cut -c1-200)"
}
export -f job; export W
{
for L in 0 1; do for r in qkv gu od; do echo "L${L}_$r $MB --run $r --ages $SA --fixture $FX/L${L}_mat_$r.npz"; done; done
echo "lm $MB --run lm --ages $SA"
echo "emb $MB --run emb --ages $SA"
echo "MUT_L0_qkv_sbase1 $MB --run qkv --mutant sbase1 --ages $SA --fixture $FX/L0_mat_qkv.npz"
echo "MUT_L0_gu_sbase1 $MB --run gu --mutant sbase1 --ages $SA --fixture $FX/L0_mat_gu.npz"
echo "MUT_L0_od_nostagger $MB --run od --mutant nostagger --ages $SA --fixture $FX/L0_mat_od.npz"
echo "MUT_lm_amax_local $MB --run lm --mutant amax_local --ages $SA"
echo "MUT_emb_emb_late $MB --run emb --mutant emb_late --ages $SA"
} | xargs -P 12 -L 1 bash -c 'job "$@"' _
echo "mat rerun $(( $(date +%s) - t0 )) s" >> $W/timing.txt
