#!/bin/bash
# run from this directory of a repo checkout; gen.py reads tools/die_plan/bind.py of the same commit
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$HOME/.local/opentallas-tools/bin:$PATH"
cd "$(dirname "$0")"
python3 gen.py
verilator --binary --timing --top-module tb -j 8 -O2 --x-initial unique --x-assign unique -Wno-fatal -Werror-WIDTH -Werror-SELRANGE ot_dp_dly.sv tb.sv --Mdir obj > build.log 2>&1
obj/Vtb +MUT=0 +verilator+rand+reset+2 > nominal.log 2>&1
for m in 1 2 3;do
 set +e
 obj/Vtb +MUT=$m +verilator+rand+reset+2 > mutant$m.log 2>&1
 rc=$?
 set -e
 test "$rc" -ne 0
 grep -q CB16_FLOW_MISMATCH mutant$m.log
done
grep CB16_PAD_FLOW_PASS nominal.log
echo CB16_FLOW_THREE_MUTANTS_CAUGHT
