#!/usr/bin/env bash
set -euo pipefail
cd /srv/opentallas-scratch/claude/codex-s81-shlk-benchfix-1021/source_1bf
O=/srv/opentallas-scratch/claude/codex-s81-shlk-benchfix-1021/static_ks6_cost
mkdir -p "$O"
cat > "$O/cost.ys" <<EOS
read_verilog -sv -DSYNTHESIS rtl/dsrom_sys/s81_dv/unit/dsdv_static_ks6.sv
hierarchy -top dsdv_static_ks6
synth -top dsdv_static_ks6 -noabc
tee -o $O/stat.json stat -json
EOS
"$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys" -Q -T -s "$O/cost.ys" > "$O/synth.log" 2>&1
