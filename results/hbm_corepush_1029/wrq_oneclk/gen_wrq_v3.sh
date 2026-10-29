#!/bin/bash
set -euo pipefail
w=/srv/opentallas-scratch2/claude/wt/codex-hbm-wrqgen-1029
r=/srv/opentallas-scratch2/claude/codex-hbm-wrqgen-1029
python3 - "$r/plan/wrq_views_v3.json" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);d=json.loads(p.read_text());d['plan']=str(p.parent/'die_plan.json');p.write_text(json.dumps(d,indent=1)+'\n')
PY
python3 "$w/results/die_hbm_kits_1027/mk_c20.py" "$r/plan" "$r/plan/wrq_views_v3.json" "$r/slices_v3" "$r/kits_v3" "$w" ot_hbm_sm_vm_wr_q_t_lanes4 --tag _oneclk1029v3 --avoid-macros "$r/macro.json" --gen-args "--recipe-key ot_hbm_sm_vm_wr_q_t_lanes4__oneclk_profile --macro-placement $r/macro.json --macro-inst-fmt {k}" > "$r/gen_v3.log" 2>&1
python3 - "$r/kits_v3/mk_c20_result.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));xs=[q for vs in r.values() for q in vs];assert len(xs)==1 and xs[0]['rc']==0 and xs[0]['kit'],xs
PY
n=0
for k in "$r"/kits_v3/*;do
 [ -f "$k/freeze.json" ] || continue
 n=$((n+1))
 python3 "$w/tools/die_plan/kit_preflight.py" --contract --plan-dir "$r/plan" --out "$r/preflight_v3.json" "$k" > "$r/preflight_v3.log" 2>&1
done
test "$n" = 1
echo WRQ_ONECLK_GEN_PREFLIGHT_DONE
