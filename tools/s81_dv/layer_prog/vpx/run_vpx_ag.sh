#!/bin/bash
# run_vpx_ag.sh <outdir> <case dir>...  (cwd = kit root = repo layout): LB2-S81/CC fork VPX end-slice all-gather vehicle.
# Builds tb_vpx_ag (two full end-slice masters u_s_0S lepw + u_s_7S lepe_nh, real lane tiles, ot_pdie_ucie) ONCE with the
# daemon Verilator 5.050, then runs every case dir (stim.txt + expect.json from gen_vpx_ag.py) and checks it.
# Sources = tools/s81_slice/slice_lep_bench.sh (main a9b56e8e3) minus its tb, plus tb_vpx_ag.sv; listed in sources.f.
set -u; O=$1; shift; mkdir -p $O
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
[ -x $V ] || { echo "NO_VERILATOR_5050"; exit 4; }
$V --version > $O/verilator.version
srcs="$(grep -v '^#' tools/s81_dv/layer_prog/vpx/sources.f | tr '\n' ' ')"
sha256sum $srcs tools/s81_dv/layer_prog/vpx/*.py tools/s81_dv/layer_prog/lower_vpx.py > $O/sources.sha256
if [ ! -x $O/obj/Vtb_vpx_ag ]; then
  /usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
    +define+DSFD_PQ_STATIC_X2 --top-module tb_vpx_ag -Mdir $O/obj $srcs --build-jobs ${J:-16} \
    -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
    || { echo "BUILD_FAILED"; grep -m10 -E "%Error" $O/build.log; exit 3; }
fi
grep -E "PINMISSING|PINCONNECTEMPTY|PINNOCONNECT" $O/build.log | grep -v tb_vpx_ag | head -8
rc=0
for C in "$@"; do
  n=$(basename $C)
  /usr/bin/time -v -o $C/time_run.log $O/obj/Vtb_vpx_ag +STIM=$C/stim.txt > $C/run.log 2>&1
  python3 tools/s81_dv/layer_prog/vpx/check_vpx_ag.py --dir $C > $C/check.out 2>&1; r=$?
  echo "CASE $n exit $r: $(head -1 $C/check.out | cut -c1-300)"
  m=$(python3 -c "import json;print(json.load(open('$C/expect.json'))['mut'])")
  if [ $m = none ]; then [ $r = 0 ] || rc=1; else [ $r = 1 ] || rc=1; fi
done
exit $rc
