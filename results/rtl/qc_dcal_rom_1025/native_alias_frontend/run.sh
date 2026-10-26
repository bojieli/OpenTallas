#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
cd "$(dirname "$0")"
yosys -Q -p 'read_verilog -sv -lib ot_rom_64x64_m2_bb.v ot_rom_4096x72_m8_bb.v; read_verilog -sv -defer -D SYNTHESIS -I . ot_qwen_d2d_ovl_seq_image64.sv ot_qwen_d2d_ovl_seq.sv ot_qwen_d2d_cal_seq_image64.sv ot_qwen_d2d_cal_seq.sv alias.sv good.v; hierarchy -check -top top; stat' > good.log 2>&1
set +e
yosys -Q -p 'read_verilog -sv -lib ot_rom_64x64_m2_bb.v ot_rom_4096x72_m8_bb.v; read_verilog -sv -defer -D SYNTHESIS -I . ot_qwen_d2d_ovl_seq_image64.sv ot_qwen_d2d_ovl_seq.sv ot_qwen_d2d_cal_seq_image64.sv ot_qwen_d2d_cal_seq.sv alias.sv bad.v; hierarchy -check -top top; stat' > bad.log 2>&1
rc=$?
set -e
if [ "$rc" -eq 0 ]; then echo "FAIL unknown metadata accepted"; exit 1; fi
grep -iE "parameter.*(not|unknown|undeclared)|does not have.*parameter|defparam.*UNKNOWN" bad.log
echo "CLASSIC FULL ALIAS PASS + negative control"
