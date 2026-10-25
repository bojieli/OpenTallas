#!/bin/bash
# QC-TOK 2026-10-25: wavefront-reset negative control on the r3 wavefront xt1 both-cluster carve (codex-qc-wavefront-run-1025/both,
# same carve/src/inputs; only tb_smoke gains +START_DELAY). Nominal START_DELAY = CALENDAR_START_DELAY 130 (> latest core pin
# release 129) must stay 64/64+64/64; a calendar started before the wavefront completes (100) or keyed to the reset edge (0) must FAIL.
set -u
W=$(cd "$(dirname "$0")" && pwd); cd $W
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep -q 5.050 || { echo "RESULT BUILD_FAIL need verilator 5.050"; exit 2; }
OBJ=$W/obj
if [ ! -x $OBJ/Vtb ]; then
  INC=$(sed "s|^|+incdir+$W/|" build_inc.f); FILES=$(sed "s|^|$W/|" build_files.f)
  /usr/bin/time -v -o build.time verilator --cc --exe --build -j 32 --build-jobs 32 --output-groups 192 \
    -CFLAGS -O0 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 \
    $(cat defines.f) --top-module tb_xt1b --prefix Vtb -Mdir $OBJ +incdir+$W/carve $INC \
    $W/bench/main2.cpp $FILES carve/xt1b_carve.v carve/tb_smoke.sv > build.log 2>&1
  [ -x $OBJ/Vtb ] || { echo "RESULT BUILD_FAIL"; grep -m20 %Error build.log; exit 2; }
fi
python3 bench/xt1_bench.py gen --gold inputs/gold_near.json --out ev.txt --mode nominal --lead 24 --gap 4 > gen.out 2>&1 || { echo GEN_FAIL; exit 2; }
GF=inputs/gold_far.json; [ -f $GF ] || GF=inputs/gold_near.json
for sd in 130 100 0; do
  /usr/bin/time -v -o sim_sd$sd.time $OBJ/Vtb +EV=$W/ev.txt +LOG=$W/log_sd$sd.txt +NCYC=6460 +OT_ROM_DIR=$W/inputs/masks \
     +SMOKE_MUT_SKEW=0 +START_DELAY=$sd > sim_sd$sd.out 2>&1; echo "sim rc=$?" >> sim_sd$sd.out
  [ -f log_sd$sd.txt ] || : > log_sd$sd.txt
  python3 bench/xt1n_bench.py check --gold-near inputs/gold_near.json --gold-far $GF --log log_sd$sd.txt --mode nominal \
     --lead 24 --gap 4 > check_sd$sd.txt 2>&1
  echo "[start_delay=$sd] $(grep -h "^RESULT" check_sd$sd.txt | tail -1)"
done
