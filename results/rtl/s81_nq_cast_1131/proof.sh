#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-s81-nq-cast-1131
iverilog -g2012 -s tb -o proof.vvp tb.sv
vvp proof.vvp > proof.log
cat proof.log
docker run --rm --memory=2g --memory-swap=2g --cpus=1 -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -T -p "read_verilog -sv dsdv_idx_rg3_nq_native.sv" > yosys_retry.log 2>&1'
tail -n 5 yosys_retry.log
