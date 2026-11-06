#!/bin/bash
# run_bench.sh NAME VAR MUT SEED [HP SP]: build + run one lock-step config (verilator 5.050, 8 GB cap)
set -u; B=$(cd $(dirname $0); pwd); N=$1; V=$2; M=$3; S=$4; HP=${5:-512}; SP=${6:-417}
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
X="${XD:-} -DVAR=$V -DMUTN=$M -DSEED=$S -DHP=$HP -DSP=$SP"; [ $V = 0 ] && X="$X -DEXACT"; [ $V = 1 ] && X="$X -DVB_INV"
rm -rf $B/obj_$N; cd $B
prlimit --as=8000000000 nice -n 10 $VL --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_svgr_bk_b12 $X   --Mdir obj_$N -o sim tb_svgr_bk_b12.sv ot_svgr_bk_b12.sv ref_b8.sv > build_$N.log 2>&1 || { echo "$N BUILD_FAIL"; tail -20 build_$N.log; exit 1; }
prlimit --as=8000000000 timeout 3000 ./obj_$N/sim > sim_$N.log 2>&1; echo "$N $(grep -h 'BENCH ' sim_$N.log | tail -2 | tr '\n' ' ')"
