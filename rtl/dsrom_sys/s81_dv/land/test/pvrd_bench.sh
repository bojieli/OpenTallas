#!/bin/bash
# S81-DIE5 / S81-DIE7 PVRD (10-18): dsfd_dvland_pvrd bench (iverilog), runnable from any cwd (kit benches run it from the
# repo root of the job's source snapshot).
#   usage: pvrd_bench.sh MODE OUTDIR      MODE = pass | mut_cal | mut_sel
#   pass    : base RTL; lane dL 300 / 700 / 1100 ps (K 2 / 2 / 3), a 160-word job (the compiler's nw), and a calendar
#             slip (one moved head flag) that MUST raise fault.  Every base case checks every RD beat (kind, pairs, leaf,
#             row, word, zero tail), ONE constant latency equal to the case's calendar latency (LAT, edges), fault 0.
#   mut_cal : -DMUT1 (dsfd_dvland_pvrd MUT=1: leaf calendar off by one)              -> must FAIL
#   mut_sel : -DOT_S81_LAND_MUT_SEL (ring read slot one late, the K-1 calendar)       -> must FAIL (latency / fault)
# Last line: "PVRD_BENCH PASS <n> cases" or "PVRD_BENCH FAIL <reason>".
set -u
here=$(cd "$(dirname "$0")" && pwd); land=$(dirname "$here")
mode=${1:-pass}; out=${2:-./pvrd_bench_run}; mkdir -p "$out"
case $mode in
    pass) defs="" ;;
    mut_cal) defs="-DMUT1" ;;
    mut_sel) defs="-DOT_S81_LAND_MUT_SEL" ;;
    *) echo "PVRD_BENCH FAIL unknown mode $mode"; exit 2 ;;
esac
iverilog -g2012 $defs -o "$out/b_$mode" "$here/tb_dsfd_dvland_pvrd.sv" "$land/dsfd_dvland_pvrd.sv" "$land/ot_s81_land.sv" \
    || { echo "PVRD_BENCH FAIL compile"; exit 2; }
# case = plusargs; LAT = the calendar latency of the reference calendar (last station edge -> o, in the bench's edge
# count) for that dL / K: it does not depend on the job length and must not move under a calendar mutant.
n=0; bad=0
for a in "DL=300 K=2 LAT=5" "DL=700 K=2 LAT=6" "DL=1100 K=3 LAT=7" "DL=300 K=2 NW=160 LAT=5" "DL=300 K=2 SLIP=1"; do
    r=$(vvp -n "$out/b_$mode" $(for x in $a; do echo +$x; done) | grep -E "OT_PVRD|PVRD_RESULT")
    echo "case $a"; echo "$r"
    n=$((n + 1))
    echo "$r" | grep -q "PVRD_RESULT PASS" || bad=$((bad + 1))
done
if [ $bad -eq 0 ]; then echo "PVRD_BENCH PASS $n cases"; exit 0; fi
echo "PVRD_BENCH FAIL $bad of $n cases ($mode)"; exit 1
