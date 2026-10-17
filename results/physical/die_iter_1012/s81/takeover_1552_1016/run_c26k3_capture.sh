#!/bin/bash
set -uo pipefail
B=/srv/opentallas-scratch/codex/s81-die-1552
S=$B/source_3f21ae39b
W=$B/c26k3_capture_hubfirst
[ ! -e "$W" ] || exit 2
mkdir "$W"
cd "$S"
export PYTHONPATH=/srv/opentallas-scratch/claude/s81-die-r10/deps
export OT_S81_DIAGNOSTIC_CLOSED_VIEWS=1 OT_S81_VIEW_BINDING_SKIP_MISFIT=1 OT_S81_STATION_FALLBACK=1 OT_PIN_ALIGN_GATE=warn OT_S81_PAIR_GATE=0 OT_S81_CTRL_GATE_WARN=phys OT_S81_Q_LEF=physical/s81_die_views/q_elem_qs5f_efs/q_elem.lef.gz
A="$(cat /srv/opentallas-scratch/claude/sdie-hubv3i/gen26i_v3i5_test.opts) --cfifo-colck --hub-first-stations --wfc-return256 --pqcnt-lef-pins --view-binding results/arch/s81_native_20261013/view_binding_closed_sdie_c26j.json --capture-source-packet physical/s81_die_pins/capture_split_1016/source_current_binding.json.gz"
printf '%s\n' "$A" > "$W/options.txt"
date -Is > "$W/start"
python3 tools/dsrom_s81_fulldie.py real $A --work "$W/a_real" > "$W/gen.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$W/gen.exit"
printf 'GEN_EXIT %s\n' "$rc" >> "$W/gen.log"
date -Is > "$W/end"
exit "$rc"
