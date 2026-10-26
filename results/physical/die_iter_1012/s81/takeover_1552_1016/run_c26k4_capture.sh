#!/bin/bash
set -uo pipefail
B=/srv/opentallas-scratch/codex/s81-die-1552
S=$B/source_946bddbe3
W=$B/c26k4_capture_protected_rehome
[ ! -e "$W" ] || exit 2
mkdir "$W"
cd "$S"
export PYTHONPATH=/srv/opentallas-scratch/claude/s81-die-r10/deps
export OT_S81_DIAGNOSTIC_CLOSED_VIEWS=1 OT_S81_VIEW_BINDING_SKIP_MISFIT=1 OT_S81_STATION_FALLBACK=1 OT_PIN_ALIGN_GATE=warn OT_S81_PAIR_GATE=0 OT_S81_CTRL_GATE_WARN=phys OT_S81_Q_LEF=physical/s81_die_views/q_elem_qs5f_efs/q_elem.lef.gz
python3 - <<'OPTIONS'
from pathlib import Path
b=Path('/srv/opentallas-scratch/codex/s81-die-1552');w=b/'c26k4_capture_protected_rehome'
base=Path('/srv/opentallas-scratch/claude/sdie-hubv3i/gen26i_v3i5_test.opts').read_text().strip()
extra=' --cfifo-colck --hub-first-stations --wfc-return256 --pqcnt-lef-pins --view-binding results/arch/s81_native_20261013/view_binding_closed_sdie_c26j.json --capture-source-packet physical/s81_die_pins/capture_rehome_1552/candidate4_packet.json.gz'
(w/'options.txt').write_text('real '+base+extra+' --work '+str(w/'a_real')+'\n')
OPTIONS
date -Is > "$W/start"
python3 tools/s81/sstn_split_diag.py --root "$S" --options "$W/options.txt" --out "$W/a_real" > "$W/gen.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$W/gen.exit"
printf 'GEN_EXIT %s\n' "$rc" >> "$W/gen.log"
date -Is > "$W/end"
exit "$rc"
