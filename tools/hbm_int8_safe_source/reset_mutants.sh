#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p reset_mutants
python3 - <<'MUT'
from pathlib import Path
s=Path('rtl/hbm_accel/sm/static/ot_smh_int8_tile_safe.sv').read_text()
assert s.count('reset_final <= {9{reset_first}};')==1
Path('reset_mutants/short.sv').write_text(s.replace('reset_final <= {9{reset_first}};', 'reset_final <= {9{rst_n}};'))
Path('reset_mutants/long.sv').write_text(s.replace('(* keep *) reg reset_first;', '(* keep *) reg reset_first; reg reset_middle; always @(posedge clk) reset_middle<=reset_first;').replace('reset_final <= {9{reset_first}};', 'reset_final <= {9{reset_middle}};'))
MUT
for m in short long; do
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_smh_int8_tile_safe_reset --Mdir reset_mutants/${m}_obj -o tb rtl/hbm_accel/sm/static/test/tb_smh_int8_tile_safe_reset.sv rtl/hbm_accel/sm/static/ot_smh_int8_tile.sv reset_mutants/$m.sv > reset_mutants/${m}_build.log 2>&1
if reset_mutants/${m}_obj/tb > reset_mutants/${m}_run.log 2>&1; then echo "RESET MUTANT UNCAUGHT $m";exit 1;fi
grep -E 'RESET (LOCKSTEP|STAGE) FAIL' reset_mutants/${m}_run.log
 done
