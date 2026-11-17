#!/bin/bash
set -eu
R=$(cd "$(dirname "$0")/../.." && pwd)
L=${1:?fresh output directory}
mkdir -p "$L"
cp "$R/results/head_rmstage_1116/tb_rmstage_eq.sv" "$L/"
SRC=$R/rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv
cd "$L"
python3 -I - "$SRC" <<'PY'
import sys
from pathlib import Path
s=Path(sys.argv[1]).read_text();s=s[s.index('module ot_s81_rate_match #'):];s=s[:s.index('endmodule')+9]
Path('base.sv').write_text(s.replace('module ot_s81_rate_match #','module ot_s81_rate_match_base #',1))
Path('stage.sv').write_text('`define OT_S81_RM_STAGED\n'+s.replace('module ot_s81_rate_match #','module ot_s81_rate_match_stage #',1))
PY
for g in 0 1; do
for f in 1 0; do
  iverilog -g2012 -s tb -Ptb.FAST=$f -Ptb.GAPS=$g -o eq${f}_${g}.vvp tb_rmstage_eq.sv base.sv stage.sv > build${f}_${g}.log 2>&1
  vvp eq${f}_${g}.vvp > run${f}_${g}.log 2>&1
  grep RMSTAGE_EQ run${f}_${g}.log
done
done
iverilog -g2012 -s tb -Ptb.FAST=1 -DRMMUT_NOSTAGE -o mutant.vvp tb_rmstage_eq.sv base.sv stage.sv > build_mutant.log 2>&1
if vvp mutant.vvp > run_mutant.log 2>&1; then echo MUTANT_ESCAPED;exit 1;fi
grep 'RMSTAGE_EQ.*FAIL' run_mutant.log
echo RMSTAGE_MUTANT_DETECTED

iverilog -g2012 -s tb -Ptb.FAST=1 -DRMSTAGED_MUT_STALE -o stale.vvp tb_rmstage_eq.sv base.sv stage.sv > build_stale.log 2>&1
if vvp stale.vvp > run_stale.log 2>&1; then echo STALE_MUTANT_ESCAPED;exit 1;fi
grep "RMSTAGE_EQ.*FAIL" run_stale.log
echo RMSTAGE_STALE_MUTANT_DETECTED
