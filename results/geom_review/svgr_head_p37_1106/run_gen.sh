#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
TASK_ROOT=$PWD
TOOL="$TASK_ROOT/wt/physical/die_plan/hbm_arch_cores"
PLAN=/srv/opentallas-scratch2/claude/codex-hbm-wave/d44v37/die_plan.json
python3 "$TOOL/views_b2r2.py" --plan "$PLAN" --out "$TASK_ROOT/views_p37.json"
python3 - "$TASK_ROOT" <<'PY'
import pathlib,json,sys,hashlib
p=pathlib.Path(sys.argv[1]); j=json.loads((p/'views_p37.json').read_text());v=next(x for x in j['view_list'] if x['view']=='ot_svgr_own@2054dcac0c09');assert v['outline_um']==[129.6,432.0];assert v['pins_sha256'].startswith('2054dcac0c09');j['view_list']=[v];j['views']=1;(p/'views_own.json').write_text(json.dumps(j,indent=2)+'\n'); print(json.dumps(v,indent=2))
PY
python3 "$TOOL/gen_core_kit_hbm.py" --views "$TASK_ROOT/views_own.json" --view ot_svgr_own@2054dcac0c09 --recipe-key ot_svgr_own__headtail --out "$TASK_ROOT/kits" --corner TC --sigmax M5 --face-shell on --clock-taps density --clock-tap-sinks 1250 --clock-tap-dmax 80 --tag headtail_p37
python3 "$TOOL/review_core.py" --views "$TASK_ROOT/views_own.json" --view ot_svgr_own@2054dcac0c09 --out "$TASK_ROOT/review"
python3 "$TASK_ROOT/render_actual.py"
