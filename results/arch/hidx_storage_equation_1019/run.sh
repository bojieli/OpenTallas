#!/bin/bash
set -eu
python3 proof.py > equations.log
verilator --version > verilator.version
verilator --binary --timing -Wno-fatal -j 2 --top-module tb --Mdir obj tb.sv original.v slice.v >build.log 2>&1
./obj/Vtb > positive.log 2>&1
for m in 1 2 3 4; do
 set +e
 ./obj/Vtb +mut=$m > mutant_$m.log 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ]; then exit 12; fi
 grep -q PROJECTION_FAIL mutant_$m.log
done
sha256sum original.v slice.v proof.py tb.sv mem_compiler/*.py > SHA256SUMS
