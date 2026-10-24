#!/bin/bash
# TOK-DS/COMP 10-24: regenerate the dense XS4/frame/CAP component vectors on the current die tree and run the bench.
# Commands follow results/token_pass/s81_dense_source_1021/README.md (vec_B_kv_landed_current recipe).
# run_dense_xs_cap_1024.sh WT OUT TREE FIXTURES_L0 [J]
set -uo pipefail
WT=$1; O=$2; TREE=$3; FIX=$4; export J=${5:-8}; mkdir -p $O/fs
cd $WT; git rev-parse HEAD > $O/main_sha.txt
step() { echo "== $*" >> $O/steps.log; "$@" >> $O/steps.log 2>&1; r=$?; echo "rc $r" >> $O/steps.log; return $r; }
step python3 tools/s81_dv/frame_schedule.py results/arch/s81_dv_1016/frame_l4_cluster/compiler/col_h9_spec.json --out $O/fs/col_h9_schedule.json || exit 11
step python3 tools/s81_dv/frame_schedule.py results/arch/s81_dv_1016/frame_l4_cluster/compiler/col_h10_spec.json --out $O/fs/col_h10_schedule.json || exit 12
export OT_XS_APROJ_TOPO=1 OT_XS_APROJ_ALIGN4=1 OT_XS_APROJ_RANK_TAGS=1 OT_XS_DENSE_SPLIT2=B OT_XS_APROJ_CAP_PLAN=1 OT_XS_FRAME_SCHEDULE_DIR=$O/fs
step python3 tools/s81_dv/layer_prog/aproj_native_pair_map.py --tree $TREE --fixtures $FIX --out $O/capture-map.json || exit 13
export OT_XS_DENSE_SPLIT2=B
step python3 tools/s81_dv/layer_prog/lower_xs.py gen --die-src $TREE --fixtures $FIX --slice u_s_2N --frame u_f_2L13 --out $O/vec --cycles 4000 || exit 14
step python3 tools/s81_dv/tokfunc/dense_xs_program.py --vectors $O/vec --capture-map $O/capture-map.json || exit 15
step bash tools/s81_dv/tokfunc/run_dense_xs_cap.sh $O/run $O/vec; rd=$?
python3 -I tools/verilator_nba_guard.py $O/run/obj > $O/nba.txt 2>&1; echo "rc $?" >> $O/nba.txt
echo "DONE rc_bench=$rd"
