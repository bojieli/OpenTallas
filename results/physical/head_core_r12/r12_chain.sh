#!/bin/bash
# HEAD-CORE-R12 chain (run ON the kit host via ot-run): LEC of the HOLD-REPAIRED export (gold = r11 CY_COPY RTL,
# kit KIT.lec_r11 built by head-core-r11/r11_collect.sh) -> gate (EQUIVALENT + KEEP: no missing kept bit, no dead
# chain-head g_s[0] cy copies) -> route + finish + signoff (actual_head_route_r12.sh, 48 GB / 16 t).
#   r12_chain.sh KIT
set -euo pipefail
K=$(realpath "$1"); L=$K.lec_r11; D=$(dirname "$(realpath "$0")")
exec >> "$K/r12_chain.log" 2>&1   # self-logging: survives a closed caller pipe
echo "R12_CHAIN start $(date -Is) kit $K"
python3 -I "$L/lec.py" "$L" --netlist "$L/actual_functional.v" --out "$L/lec" --jobs 8 --mem 16 > "$L/lec.run.log" 2>&1 || echo "lec.py rc=$?"
tail -n 2 "$L/lec.run.log"
python3 -I - "$L/lec" <<'PY'
import json, sys, re
from pathlib import Path
o = Path(sys.argv[1]); d = json.loads((o/'lec.json').read_text())
kr = d.get('kept_registers', {}); keep = (o/'gold.keep').read_text().splitlines()
dead = [k for k in keep if 'g_cy_copy' in k and 'g_s[0]' in k]
print('R12_LEC verdict', d['verdict'], d.get('counts'), 'kept declared', kr.get('declared'), 'in_netlist', kr.get('in_netlist'),
      'missing', kr.get('missing', {}).get('n'), 'const_proved', kr.get('constant_proved', {}).get('n'), 'dead g_s[0] cy copies', len(dead))
assert d['verdict'] == 'EQUIVALENT', d['verdict']
assert kr.get('missing', {}).get('n') == 0, kr.get('missing')
assert not dead, dead[:4]
PY
echo "R12_LEC_GATE PASS $(date -Is)"
bash "$D/actual_head_route_r12.sh" "$K" 48 16
echo "R12_CHAIN route+signoff rc=0 $(date -Is)"
grep -h SIGNOFF "$K/signoff_actual.log" || true
