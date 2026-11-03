#!/bin/bash
set -euo pipefail
ulimit -c 0
R=/srv/opentallas-scratch2/claude/codex-ds-bf-native-pair-0605
cd "$R"
for name in wrong_operand wrong_date wrong_class wrong_status late_accept initial_GW_family0 wrong_write_bank; do
 extra=(); [[ "$name" == wrong_status ]] && extra=(+bad_status=1)
 ./obj/Vtb_bf_source_pair +OT_ROM_DIR="$R/$name" "${extra[@]}" > "$name.log" 2>&1
done
