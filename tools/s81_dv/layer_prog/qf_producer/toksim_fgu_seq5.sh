#!/bin/bash
# TOKSIM-S81B/FGU 10-19 job 5: shared_gu + experts_gu back to back on the frame (28 phases, +RETIRE=1, job 4's exe), and
# the experts_gu floor between 140 (FAIL) and 145 (PASS), shared_gu at 146.  cwd = src root; args: VEC FIX OUT4 OUT
set -u
VEC=$(realpath $1); FIX=$(realpath $2); X=$(realpath $3)/obj/Vtb_toksim_fgu_seq; O=$(realpath -m $4); mkdir -p $O
Q=tools/s81_dv/layer_prog/qf_producer
python3 $Q/toksim_fgu_seqall.py $VEC
{
 for P in 145 147 150 160 200; do echo "seq_gu_all $P 28 16"; done
 for P in 141 142 143 144; do echo "seq_experts_gu $P 24 20"; done
 echo "seq_shared_gu 146 4 16"
} | xargs -P 16 -L1 bash -c 'sn=$0; P=$1; n=$2; ph0=$3; tg=${sn}_P${P}_R1;
  timeout 900 stdbuf -oL '$X' +OT_ROM_DIR='$VEC'/$sn +T=1600 +K=5120 +OPS=4 +PH=$ph0 +NPH=$n +PER=$P +RETIRE=1 > '$O'/run_$tg.log 2>&1;
  echo "$tg rc=$? $(python3 '$Q'/toksim_fgu_check.py seq --seq '$VEC'/$sn --vec '$VEC' --fixtures '$FIX' --log '$O'/run_$tg.log --out '$O'/res_$tg.json --per $P --ref-go 63 2>&1 | tail -1)"' | sort -V | tee $O/sweep.txt
echo TOKSIM_FGU_SEQ5_DONE
