#!/bin/bash
set -euo pipefail
TASK=/srv/opentallas-scratch2/claude/codex-ds-norm-event3-1030
TOOLING=/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029
export PYTHONPATH="$TASK/code:$TASK/code/layer_prog:$TOOLING/tools/s81_dv:$TOOLING/tools/die_plan"
python3 -m layer_prog.selected_entry_norm --source-inventory /srv/opentallas-scratch2/claude/codex-s81-inventory-1030/inventory.json --fixtures /srv/opentallas-scratch2/claude/tok-ds/s81_877/l14_prog/fix/L14 --entry-engram-inputs /srv/opentallas-scratch2/claude/codex-ds-entry-current-1030/engram_L14 --inference-config "$TOOLING/compiler/models/deepseek-v4.1-flash/inference_config.json" --first-issue 20 --out "$TASK/L14"
