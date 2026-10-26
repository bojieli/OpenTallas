#!/bin/bash
set -e
D=$(cd "$(dirname "$0")" && pwd)
cd "$D"
sudo docker run --rm --name codex-kvhr-ingest-lint3 --memory 16g -v "$D":/w -w /w openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -T -p 'read_verilog -defer -sv -DSYNTHESIS ot_sram_1r1w_32x128_m1_bb.v ot_hdc_ingest_fp8q.sv candidate.sv lint_top.sv; hierarchy -top lint_top; proc; check -assert' > lint.log 2>&1
V=$HOME/.local/opentallas-tools/bin/verilator
for mut in 0 1; do
 "$V" --binary --timing -O1 -j 8 --output-split 10000 --output-split-cfuncs 100 -CFLAGS -O0 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD --top-module tb -GMUT=$mut --Mdir obj$mut tb.sv gold.sv candidate.sv ot_hdc_ingest_fp8q.sv ot_sram_1r1w_32x128_m1.v > build$mut.log 2>&1
 set +e; ./obj$mut/Vtb > run$mut.log 2>&1; rc=$?; set -e
 if [ $mut = 0 ]; then test $rc = 0; grep 'PASS INGEST_LOCKSTEP' run0.log; else test $rc != 0; grep 'LOCKSTEP' run1.log; fi
done
