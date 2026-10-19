#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
cd "$D/src"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mut=$1
rc=0
python3 tools/qwen_coll_tp8_static_bench.py --out "$D/out" --latu 65 --lats 390 --qfd --pr-b4 --production --only '^qwen_ar_256w$' --mutant-define "$mut" || rc=$?
python3 - "$D/out/record.json" "$rc" "$mut" <<'CHECK'
import json,sys
r=json.load(open(sys.argv[1]));c=r['cases'][0]
assert int(sys.argv[2])==1 and r['mutant']==sys.argv[3] and not c['exact'] and c['mismatches']>0
print('B4_CORE_MUTANT_CAUGHT',sys.argv[3], 'mismatches='+str(c['mismatches']), 'fault='+c['fault'])
CHECK
