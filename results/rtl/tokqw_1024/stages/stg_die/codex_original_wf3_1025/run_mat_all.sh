#!/bin/bash
set -eu
E=$(cd "$(dirname "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
bash "$E/tree/tools/qwen_tokfunc/stage_stg_die.sh" "$E" "$E/stg_result.json" "$E/pos_mat_runlist.txt" --par 24
python3 - "$E/stgdie/result.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));print('MAT_FAMILIES',r['verdict'],r['matched_pos'],'/',r['cases_total']);raise SystemExit(0 if r['verdict']=='PASS' else 1)
PY
