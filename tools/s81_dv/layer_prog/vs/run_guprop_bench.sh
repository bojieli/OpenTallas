#!/bin/bash
# run_guprop_bench.sh <kit root R> <out O> <VS_MUT> <vec dir>... : DRIVE-S81-GUPROP SW-consumer bench (tb_vs_guprop.sv) on the
# REAL ot_s81sl_vp + ot_s81sl_vs + ot_s81sl_vsw + RA lane pair + ot_s81sl_vq (file list of run_vs_bench.sh), Verilator 5.050
# (the closure daemon's pin).  Builds once per VS_MUT, runs every vector dir (gen_guprop_bench.py output).
#   GPB <vec> PASS|FAIL + the tb's GUPROP_SPAN / VSOP / SLVSL lines.  Exit 0 always; the verdict is in the logs.
set -u
R=$(realpath $1); O=$2; M=$3; shift 3; mkdir -p $O; O=$(realpath $O)
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
S=$(sed -n '/^S="/,/vs\/tb_vs_lowered.sv"/p' $R/tools/s81_dv/layer_prog/vs/run_vs_bench.sh | sed 's/^S="//; s/"$//; s#tools/s81_dv/layer_prog/vs/tb_vs_lowered.sv#tools/s81_dv/layer_prog/vs/tb_vs_guprop.sv#')
F=""; for f in $S; do F="$F $R/$f"; done
$V --version > $O/verilator.version
(cd $R && sha256sum $S tools/s81_dv/layer_prog/lower_vs.py tools/s81_dv/layer_prog/gu_gather.py tools/s81_dv/layer_prog/xs_place.py \
   tools/s81_dv/layer_prog/vs/gen_vs_bench.py tools/s81_dv/layer_prog/vs/gen_guprop_bench.py \
   tools/s81_dv/layer_prog/vs/run_guprop_bench.sh) > $O/sources.sha256
B=$O/obj_m$M
if [ ! -x $B/Vtb_vs_guprop ]; then
  /usr/bin/time -v -o $O/build_m$M.time $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GVS_MUT=$M --top-module tb_vs_guprop \
    -Mdir $B $F --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build_m$M.log 2>&1 \
    || { echo "GPB BUILD_FAILED"; grep -m8 %Error $O/build_m$M.log; exit 3; }
fi
for d in "$@"; do
  d=$(realpath $d); n=m${M}_$(basename $d)
  (cd $d && $B/Vtb_vs_guprop $(cat params.txt) > $O/$n.run.log 2>&1)
  v=$(grep -m1 -E '^(PASS|FAIL)$' $O/$n.run.log || echo NOVERDICT)
  echo "GPB $n $v"; grep -E '^(GUPROP_SPAN|VSOP|SLVSL|MISMATCH|XQ MISMATCH)' $O/$n.run.log | head -6
done
