#!/bin/bash
# el1011-qseam: generate, verilate (Verilator 5.050) and run one Qwen die seam bench under a memory cap; writes
# <work>/<tag>/{expect.json,sim.log,verdict.json}.  Run on a fleet host (ot-epyc1tb / ot-epyc4), never localhost.
#   run.sh <work> <tag> <mem_GB> --bench array|p2p|credit [--deskew] [--mut M ...]
# env: QS_SRC (dir holding tools/qwen_die_seam, rtl/physical/ot_qwen_die_station.sv, the contract), QS_SEAMS, QS_REC,
#      QS_CONTRACT (optional: contract path; default \$QS_SRC/results/arch/hier_contract_1011/qwen_rom.json),
#      QS_GEN_ARGS (optional extra gen_bench.py args, e.g. --tile-subset for the 768-tile TP8 die)
set -euo pipefail
W=$1; TAG=$2; MEM=$3; shift 3
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
D=$W/$TAG; mkdir -p $D
python3 $QS_SRC/tools/qwen_die_seam/gen_bench.py --seams $QS_SEAMS --rec $QS_REC \
  --contract ${QS_CONTRACT:-$QS_SRC/results/arch/hier_contract_1011/qwen_rom.json} --out $D ${QS_GEN_ARGS:-} "$@" > $D/gen.log
TB=$(ls $D/qseam_*_tb.sv); TOP=$(basename $TB .sv)
cap(){ timeout 6h systemd-run --user --scope -q -p MemoryMax=${MEM}G -p MemorySwapMax=0 -- "$@"; }
( cd $D && cap verilator --binary -O3 --x-initial fast -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN \
    --top-module $TOP -j 16 --Mdir obj $QS_SRC/rtl/physical/ot_qwen_die_station.sv $TB > build.log 2>&1 )
( cd $D && cap ./obj/V$TOP > sim.log 2>&1 ) || true
python3 $QS_SRC/tools/qwen_die_seam/summarize.py --expect $D/expect.json --log $D/sim.log --out $D/verdict.json
