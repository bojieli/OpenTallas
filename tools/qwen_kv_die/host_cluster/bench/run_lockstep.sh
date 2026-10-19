#!/bin/bash
# KVJ-A3 composition bench: verilate the flat root and the generated cluster, link one harness, run seeds/modes.
# Run from a directory that holds the repo-relative sources (rtl/, physical/asap7_memory_macros/), files.txt (the
# census source list), qkd_hr_cluster.v and tb.cpp.  usage: run_lockstep.sh [VERILATOR_ROOT_BIN_DIR]
set -eo pipefail
V=${1:-verilator}
SRAM=$(ls physical/asap7_memory_macros/ot_sram_*/ot_sram_*.v | grep -v '_bb.v$')
FILES=$(cat files.txt)
COMMON="--cc -O2 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --no-timing \
 -Irtl -CFLAGS -O1 -CFLAGS -fno-var-tracking -j 0"
PRM="-GENABLE_SERVICE=1 -GENABLE_NATIVE=1 -GENABLE_TOKEN=1 -GNL=2"
[ -f obj_clu/Vclu__ALL.a ] || {
$V $COMMON --prefix Vflat --top-module qkd_host_root_admission $PRM -Mdir obj_flat $SRAM $FILES > vl_flat.log 2>&1 &
$V $COMMON --prefix Vclu --top-module qkd_hr_cluster -Mdir obj_clu $SRAM $FILES qkd_hr_cluster.v > vl_clu.log 2>&1 &
wait %1; wait %2
make -s -j 32 -C obj_flat -f Vflat.mk Vflat__ALL.a verilated.o verilated_threads.o > mk_flat.log 2>&1 &
make -s -j 32 -C obj_clu -f Vclu.mk Vclu__ALL.a > mk_clu.log 2>&1 &
wait %1; wait %2
}
VR=$($V --getenv VERILATOR_ROOT)
g++ -O1 -std=c++17 -Iobj_flat -Iobj_clu -I$VR/include -I$VR/include/vltstd tb.cpp obj_flat/Vflat__ALL.a obj_clu/Vclu__ALL.a \
 obj_flat/verilated.o obj_flat/verilated_threads.o -pthread -latomic -o tb_lockstep
for s in 1 2 3; do for m in 0 1; do ./tb_lockstep $s $m 20000; done; done
