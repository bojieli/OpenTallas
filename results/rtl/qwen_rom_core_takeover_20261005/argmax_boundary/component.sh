#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/codex/qwen-rom-argmax-component-20261005
cd "$R/src"
mkdir -p "$R/component"
python3 tools/qwen_rom_core_takeover_component.py --out "$R/component/component.sv"
for v in 0 1; do
  iverilog -g2012 -Irtl/hdc -s tb -Ptb.VPOS=$v -o "$R/component/v$v.vvp" "$R/component/component.sv" rtl/test/tb_qwen_rom_dec_la_takeover.sv rtl/hdc/ot_hdc_dyn_ttiles.sv rtl/hdc/ot_hdc_prefix.sv > "$R/component/compile_v$v.log" 2>&1
  vvp "$R/component/v$v.vvp" > "$R/component/run_v$v.log" 2>&1
  echo $? > "$R/component/run_v$v.exit"
done
