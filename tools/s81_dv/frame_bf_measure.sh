#!/bin/bash
# frame_bf_measure.sh <outdir> <M=h9|h10> <measvec> [REC.json] (cwd = repo root; FLEET via ot-run, ~6-10 GB build):
# S81-P8 10-23 -- the BF16 return-calendar MEASUREMENT on the banded LP frame with plan-width seams (vgcs twin,
# rtl/dsrom_sys/s81_dv/frame_lp/vgcs/col_<M>_l4_lp_rf3r.sv), as tools/s81_dv/layer_prog/xs/xs_bench.sh BF_LEGACY=1 does on
# the _l4 frame: frame_bench.sh FRAME_LP=1 BF_LEGACY=1 (patched core COPY issues on its walker + TB_BFTRACE; the plan
# set runs on the same build), then the measurement vector <measvec> (xs_place.py gen --bf-measure --phase <k>), then
#   xs_bf.py measure --frame lp   (descriptor fit + per-column partial edges; key col_<M>_lp|E<LK>|bseg1024)
# Env: BF_FIXTURES (fixture dir when the vector's is not on this host), LK (the die frame's lane strap E; default 2), LDLY (landing window (LK - 4) T < dL < LK T), TWIN, J.
set -u
O=$1; M=$2; VEC=$3; REC=${4:-}; MASTER=col_$M; mkdir -p $O
TW=${TWIN:-rtl/dsrom_sys/s81_dv/frame_lp/vgcs/${MASTER}_l4_lp_rf3r.sv}
BF_LEGACY=1 FRAME_LP=1 SET=plan FRAME_LP_SV=$TW LK=${LK:-2} bash tools/s81_dv/frame_bench.sh $O $MASTER 0 > $O/frame_bench.log 2>&1
echo "PLAN_SET $(grep -m1 '^FRAME_SET' $O/frame_bench.log)"
[ -x $O/obj/Vtb_s81dv_frame ] || { echo "BUILD_FAILED"; tail -n 5 $O/frame_bench.log; exit 3; }
rm -rf $O/measvec; cp -r $VEC $O/measvec
$O/obj/Vtb_s81dv_frame $(sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR=$(realpath $O/measvec)#" $VEC/ARGS) > $O/run_measure.log 2>&1
echo "MEASURE_RUN rc=$? $(grep -m1 '^END' $O/run_measure.log)"
python3 tools/s81_dv/layer_prog/xs_place.py check --dir $O/measvec --log $O/run_measure.log ${BF_FIXTURES:+--fixtures $BF_FIXTURES} | tail -n 1
python3 tools/s81_dv/layer_prog/xs_bf.py measure --frame lp --log $O/run_measure.log --vec $O/measvec --lk ${LK:-2} \
  --out ${REC:-$O/measure.json}
