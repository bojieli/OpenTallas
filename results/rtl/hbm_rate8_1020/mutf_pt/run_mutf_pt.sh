#!/usr/bin/env bash
# HBM-RATE8 10-20: COLLFUSE2 TP-8 qw8_* causal witnesses re-run on CURRENT MAIN plumbing with PRETREE=1 (closed HH-6 pre-tree bound,
# tree_cmd driven from tree.mem; vectors from prod_compile.py --pretree). POS must PASS, +MUT_FORCE (lane 0 of VM read 0 := +0x7f000000) must FAIL.
cd "$(dirname "$0")" || exit 9
RECS="qw8_softmax_max qw8_bf16_p qw8_pv_normalize qw8_round_q qw8_row_scale_qkv"
mkdir -p out
for r in $RECS; do d=vec_tp8pt/$r; rm -rf $d; mkdir -p $d
  python3 tools/hbm_static/toksim_su/suvop/prod_compile.py $d $r --rr 12 --wr 10 --pretree > $d/compile.txt 2>&1 || echo "$r COMPILE_FAIL" >> out/compile_fail.txt; done
PT=1 JOBS=${JOBS:-6} bash run_toksim_su.sh build mr10 > out/build.summary 2>&1 || { echo BUILD_FAIL > out/done.txt; exit 2; }
for r in $RECS; do
 ( PT=1 TAG=_POS bash run_toksim_su.sh run mr10 vec_tp8pt/$r > out/${r}_POS.summary 2>&1
   PT=1 TAG=_MUT_FORCE bash run_toksim_su.sh run mr10 vec_tp8pt/$r +MUT_FORCE > out/${r}_MUT_FORCE.summary 2>&1 ) &
done; wait
for r in $RECS; do d=vec_tp8pt/$r
 p=$(grep -c "SU_TOP PASS.*PRETREE=1" $d/sim_mr10_pt_POS.log); m=$(grep -c "SU_TOP FAIL" $d/sim_mr10_pt_MUT_FORCE.log)
 echo "$r POS_PASS=$p MUT_FORCE_FAIL=$m $(grep -h TOKSIM_LAST $d/sim_mr10_pt_POS.log) $(python3 -c "import json;d=json.load(open('$d/programme.json'));print('edges',d['edges'],'ser',d['cycles_serial'],'stream',d['cycles_stream_833ps'])")"
done > out/verdict.txt
sha256sum obj_mr10_pt/Vtb_toksim_su_top tb_toksim_su_top.sv run_toksim_su.sh > out/identity.sha256
echo ALLDONE > out/done.txt
