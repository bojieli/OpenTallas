#!/bin/bash
set -uo pipefail
D=$(pwd)
export OT_GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
python3 fill_physical_bind.py || exit $?
cd src || exit 2
python3 tools/s81_dv/dv_diecase.py --plan "$D/plan_realctrl/plan.json" --out "$D/bind_realctrl_v2" --bind real --bind-table results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json --land-plan results/arch/s81_dv_1016/landing/p4l3/land_plan.json > "$D/bind_realctrl_v2.log" 2>&1; echo BIND_V2_RC=$?
python3 - "$D" <<'PY2'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])/'bind_realctrl_v2/bind/port_bind.json'
if not p.exists():print('NO_PORT_REPORT');raise SystemExit(3)
x=json.loads(p.read_text());print(x['verdict']);print(x['summary']);raise SystemExit(0 if x['verdict']=='PASS' else 4)
PY2
