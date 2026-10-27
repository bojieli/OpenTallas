#!/bin/bash
# TOK-QK 10-26 QCLM-ATTNRET: the attention-return family (QW-ATTNRET, dv_lower_vec_bench --mode attn) on the QCLM
# fresh current-main (b272ba0ec) BOUND s8 slice row objects (tb_qfd_dv2 FACE 3, DV2_S8DIE=1, CROM align) + its measured
# vec ages; nominal must PASS with measured span == compiled, ddwin/ddbase mutants must FAIL.  Same protocol as
# tools/qwen_tokfunc/stage_attnret.sh (which expects rel+pos of the predecessor slice2 stg stage); the bound row is pos only.
set -u
E=/srv/opentallas-scratch2/claude/tok-qk-qclm; T=$E/tree; A=$E/attnret
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH DV2_S8DIE=1 PYTHONDONTWRITEBYTECODE=1
cd $T
for m in 0 ddwin ddbase; do d=$A/pos/$m; mkdir -p $d; ln -sfn $E/die/build/obj_n12 $d/obj_n12
  MU=""; [ $m != 0 ] && MU="--mutant $m"
  ( DV_LOWER_VFLAGS="$(cat $E/die/vflags.txt)" python3 rtl/test/qwen_dv/dv_lower_vec_bench.py --mode attn $MU --ages $E/die/build/vec_ages.json --work $d > $d/bench.out 2>&1
    echo "rc=$?" >> $d/bench.out ) &
done; wait
for m in 0 ddwin ddbase; do echo "pos $m $(grep -m1 'DV_LOWER_VEC attn' $A/pos/$m/bench.out) $(grep -m1 -oE '= [0-9]+ edges \(compiled [0-9]+\)' $A/pos/$m/bench.out)"; done | tee $A/summary.txt
