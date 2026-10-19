#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/claude/codex-s81-dieplace
cand=$base/placement_diag/coll_safe2_parent
cd "$cand/src"
python3 tools/s81_dv/coll_safe2_parent_table.py --table "$base/src/results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json" --root "$cand/src" --out "$cand/candidate_table_v2.json"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
export OT_VERILATOR=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
export OT_GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
timeout 1200 python3 tools/s81_dv/dv_diecase.py --plan "$base/plan/plan.json" --out "$cand/bound2" --bind real --bind-table "$cand/candidate_table_v2.json" --land-plan results/arch/s81_dv_1016/landing/p4l3/land_plan.json > "$cand/bind2.log" 2>&1
python3 - <<'PY'
from pathlib import Path
import json,hashlib
b=Path('../bound2/bind');c=json.loads((b/'bind_case.json').read_text());p=json.loads((b/'port_bind.json').read_text());log=(b/'port_bind.log').read_text();assert c.get('port_bind_rc')==0,c.get('port_bind_rc');assert 'STRICT PASS' in log,log[-2000:];assert 'tf' not in (b/'die.v').read_text()
Path('../STRICT_INTERFACE_PASS_V2.json').write_text(json.dumps({'port_bind_rc':c['port_bind_rc'],'port_bind_result':p,'tf_tokens':0,'die_sha256':hashlib.sha256((b/'die.v').read_bytes()).hexdigest(),'table_sha256':hashlib.sha256(Path('../candidate_table_v2.json').read_bytes()).hexdigest(),'scope':'Source-interface only; safe2 behavior/native/geometry/calendar/physical clocks not qualified'},indent=1)+'\n');print('STRICT_INTERFACE_PASS_V2')
PY
