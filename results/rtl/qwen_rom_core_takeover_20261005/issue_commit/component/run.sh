#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/codex/qwen-rom-issue-commit-component3-20261005
cd "$R/src"
mkdir -p "$R/component"
python3 tools/qwen_rom_core_takeover_component.py --am-commit --out "$R/component/component.sv"
iverilog -g2012 -Irtl/hdc -s tb -o "$R/component/test.vvp" "$R/component/component.sv" rtl/test/tb_qwen_rom_dec_commit.sv rtl/hdc/ot_hdc_dyn_ttiles.sv rtl/hdc/ot_hdc_prefix.sv > "$R/component/compile.log" 2>&1
cp results/rtl/qwen_rom_core_takeover_20261005/issue_commit/selected_head_program.hex "$R/component/"
cd "$R/component"
vvp test.vvp > run.log 2>&1
