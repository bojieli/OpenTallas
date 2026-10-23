#!/bin/bash
# TOKd-QW 10-22 optional gap stage "attnret": re-bench the attention-return family (QW-ATTNRET) on the stg stage's own
# Verilator objects and measured ages (no build).  usage: stage_attnret.sh RUNROOT STG_STAGE OBJROOT
#   RUNROOT/STG_STAGE/{tree,<cfg>/vflags.txt,<cfg>/build/vec_ages.json}; OBJROOT/<cfg> = obj_n12 of that stage.
# Runs rel + pos: nominal (must PASS, MEASURED_SPAN == compiled) + ddwin / ddbase mutants (must FAIL).
# Writes RUNROOT/attnret/result.json (stage_attnret.collect.py).
set -u
R=$(readlink -f "$1"); STG=$2; OBJ=$(readlink -f "$3"); T=$R/$STG/tree; A=$R/attnret
VB=$T/rtl/test/qwen_dv/dv_lower_vec_bench.py; HERE=$(dirname "$(readlink -f "$0")")
for c in rel pos; do for m in 0 ddwin ddbase; do d=$A/$c/$m; mkdir -p $d; ln -sfn $OBJ/$c $d/obj_n12
  MU=""; [ $m != 0 ] && MU="--mutant $m"
  DV_LOWER_VFLAGS="$(cat $R/$STG/$c/vflags.txt)" python3 $VB --mode attn $MU --ages $R/$STG/$c/build/vec_ages.json --work $d > $d/bench.out 2>&1
  echo "rc=$?" >> $d/bench.out; echo "$c $m $(head -1 $d/bench.out)"; done; done
python3 "$HERE/stage_attnret.collect.py" "$A" "$STG"
