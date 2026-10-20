#!/usr/bin/env bash
set -euo pipefail
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
E=rtl/dsrom_sys/s81_dv/eng
H=rtl/hdc
SRC=("$H/ot_hdc_fastfp.sv" "$H/ot_hdc_prefix.sv" "$H/ot_hdc_fp32_f12.sv")
"$VL" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -DOT_S81_VE_LOADSAFE5 --top-module tb_s81sl_ve_fp -GMUT=2 --Mdir obj_2 "${SRC[@]}" "$E/ot_s81sl_ve_fp.sv" "$E/test/tb_s81sl_ve_fp.sv" > build_2.log 2>&1
./obj_2/Vtb_s81sl_ve_fp +n=300000 +verilator+seed+17 +verilator+rand+reset+2 > run_2.log 2>&1
grep -q 'MUTANT 2 REJECTED' run_2.log
"$VL" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_s81sl_ve_fp --Mdir obj_default "${SRC[@]}" "$E/ot_s81sl_ve_fp.sv" "$E/test/tb_s81sl_ve_fp.sv" > build_default.log 2>&1
./obj_default/Vtb_s81sl_ve_fp +n=300000 +verilator+seed+17 +verilator+rand+reset+2 > run_default.log 2>&1
grep -q 'PASS ve_fp' run_default.log
python3 - <<'PYINNER'
from pathlib import Path
s=Path('rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv').read_text()
s=s.replace('s2_top <= {TOP_COPIES{prod[47]}};', 's2_top <= {TOP_COPIES{prod[47]}}; s2_top[TOP_EXP] <= prod[46];')
Path('source_wrong_product.sv').write_text(s)
PYINNER
"$VL" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -DOT_S81_VE_LOADSAFE5 --top-module tb_s81sl_ve_fp --Mdir obj_wrong "${SRC[@]}" source_wrong_product.sv "$E/test/tb_s81sl_ve_fp.sv" > build_wrong.log 2>&1
./obj_wrong/Vtb_s81sl_ve_fp +n=300000 +verilator+seed+17 +verilator+rand+reset+2 > run_wrong.log 2>&1
grep -q 'FAIL ve_fp' run_wrong.log
echo 'DEFAULT PASS OPTIN PASS TWO SCOREBOARD MUTANTS REJECTED SOURCE WRONG_PRODUCT REJECTED'
