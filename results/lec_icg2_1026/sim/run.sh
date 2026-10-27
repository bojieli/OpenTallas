#!/bin/bash
# LEC-ICG-2 co-sim: build NAME [prep args...]; run in docker verilator 5.032 with a memory cap.
# usage: run.sh NAME [--mutant-icg INST]
set -eu
S=/srv/opentallas-scratch2/claude/lec-icg2-1026/sim
K=/srv/opentallas-scratch2/claude/lec-icg-1026/kits/ot_v41_rom_elem_q_qxpq_w10_gb_gbcgr8
N=$K/run/results/asap7/kl_ot_v41_rom_elem_q_qxpq_w10_gb_gbcgr8/base/1_2_yosys.v
n=$1; shift
W=$S/$n; mkdir -p $W
python3 -I $S/prep_gate.py $N ot_v41_rom_elem_q_qxpq_w10_gb $K/lec/lec.json $W/gate.v $W/dbg_rtl.svh $W/dbg_names.tsv --controls 600 --drop /srv/opentallas-scratch2/claude/lec-icg2-1026/sim/drop.txt "$@" > $W/prep.log
cat $W/prep.log | head -5
[ "${LINT_ONLY:-0}" = 1 ] && exit 0
RTL=$(grep '^export VERILOG_FILES' $K/config.mk | sed 's/.*= //; s#/work/rtl/#'$K'/rtl/#g' | tr ' ' '\n' | grep -v '_bb\.v$' | tr '\n' ' ')
docker run --rm --name lecicg2-$n --memory 120g --cpus 24 -u $(id -u):$(id -g) -v $S:$S -v $K:$K:ro -w $W -e CCACHE_DISABLE=1 -e HOME=/tmp \
  --entrypoint verilator verilator/verilator:v5.032 --binary --timing -Wno-fatal -Wno-lint -Wno-style -DSYNTHESIS \
  --top-module tb_lecicg2 --Mdir $W/obj -j 24 -CFLAGS -O1 -I$W -I$K/rtl \
  $S/cells.v $RTL $W/gate.v $S/tb_lecicg2.sv > $W/build.log 2>&1 || { echo BUILD_FAIL; tail -30 $W/build.log; exit 2; }
echo BUILD_OK $n
