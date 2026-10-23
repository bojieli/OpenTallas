#!/usr/bin/env bash
# P5 price of a generated HBM plan dir: stages (stages_p5.py) + SM split R1/R2-alt/R3 (+1 SM_X, +1 SM_HBM, +3 SM_OUT,
# HBM-P4-SM measured +4 cycles/op) -> hgi_sim.plan_study_price_1017 variant b at X 377.6.  Usage: price_p5.sh PLAN_DIR TAG [--nopad]
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
O=$1; T=$2; shift 2
python3 "$D/stages_p5.py" --out "$O" --base "$R/results/arch/hbm_plan_study_1017/stages.json" --name "st_$T.json" "$@" > /dev/null
python3 - "$O/st_$T.json" "$R/results/arch/hbm_plan_study_1017/stages.json" "$O/stages_$T.json" <<'PY'
import json, sys
st = json.load(open(sys.argv[1]))['plan_v2']
for k, d in (('SM_X', 1), ('SM_HBM', 1), ('SM_OUT', 3)):
    st[k] = round(st[k] + d, 2)
base = json.load(open(sys.argv[2])); base['plan_b'] = st
json.dump(base, open(sys.argv[3], 'w'), indent=1)
PY
cd "${OT_PRICE_TOOLS:-$R/tools}" && python3 -m hgi_sim.plan_study_price_1017 --stages "$O/stages_$T.json" --x-c 377.6 --out "$O/price_$T.json" > "$O/price_$T.log" 2>&1
python3 -c "
import json,sys; d=json.load(open('$O/price_$T.json'))
print('$T', 'AR', d['table']['b|377.6']['ar_tok_s'], 'MTP', d['table']['b|377.6']['mtp_design_tok_s'], 'Qwen', d['runs']['b|qwen']['tok_s'], 'SM_X', json.load(open('$O/stages_$T.json'))['plan_b']['SM_X'])"
