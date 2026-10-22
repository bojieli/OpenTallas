#!/bin/bash
set -eu
# Run on fleet, Verilator5.050. From this evidence directory in a sparse repo.
ROOT=$(git rev-parse --show-toplevel)
python3 "$ROOT/tools/hbm_layer_vehicle/native_su_calendar.py" readback_expected.mem generated --first-serial 2675 --bridge-serial 2675 --bridge-stream 3567 --host-launch 3500 --rows 160
cp generated/calendar.mem calendar.mem
verilator --binary --timing -Wno-fatal --top-module tb --Mdir obj -j 6 readback_tb.sv exact_sources/*.sv > build.log 2>&1
obj/Vtb +CFG=config.mem +GOLD=readback_expected.mem +N=62 +W=70 > positive.log 2>&1
for m in 1 2 3; do if obj/Vtb +CFG=config.mem +GOLD=readback_expected.mem +N=62 +W=70 +MUT=$m > mutant${m}.log 2>&1; then exit 1; fi; grep -Eq 'PRODUCER FAIL|NATIVE_DATA FAIL' mutant${m}.log; done
