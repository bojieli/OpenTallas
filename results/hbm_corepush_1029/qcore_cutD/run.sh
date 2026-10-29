#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
w=/srv/opentallas-scratch2/claude/wt/codex-hbm-corepush-1029
r=/srv/opentallas-scratch2/claude/codex-hbm-cutD-1029
iverilog -g2012 -s tb_qcore_cutD -o "$r/tb" "$r/tb.sv" "$w/rtl/hdc/ot_hdc_fp32_add_n32.sv" "$w/rtl/hdc/ot_hdc_prefix.sv" > "$r/compile.log" 2>&1
vvp -n "$r/tb" > "$r/run.log" 2>&1
cat "$r/run.log"
