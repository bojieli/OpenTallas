#!/bin/bash
set -eu
O=$(realpath -m "${1:-union_out}")
C="$O/calendar"
# Expectations come from unencoded schedule tuples, not a memory readback from the DUT.
python3 - "$C" <<'PY2'
import json,sys
from pathlib import Path
sys.path.insert(0,'tools')
from hbm_next.emitter import UNIT_BIT
p=Path(sys.argv[1]);d=json.loads((p/'calendar.json').read_text());lines=[f"{d['words']} {d['stride']}"]
for v in d['variants']:
 lines.append(f"{len(v['records'])} {v['end_cycle']}")
 lines.extend(f"{r['cycle']} {UNIT_BIT[r['op'].split('.')[0]]} {r['id']}" for r in v['records'])
(p/'cases.txt').write_text('\n'.join(lines)+'\n')
PY2
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
for m in 0 1;do
 verilator --binary --timing -j 2 -Wno-fatal --top-module tb_hnx_union_compiled -GMUT=$m -Mdir "$O/cmpobj$m" \
  rtl/hbm_next/control/ot_hnx_union_calendar.sv rtl/hbm_next/control/tb_hnx_union_compiled.sv > "$O/cmp_build$m.log" 2>&1
 set +e;(cd "$C"; "$O/cmpobj$m/Vtb_hnx_union_compiled") > "$O/cmp_run$m.log" 2>&1;rc=$?;set -e
 if [ "$m" = 0 ];then [ "$rc" = 0 ];grep -q 'UNION_COMPILED PASS' "$O/cmp_run$m.log"
 else [ "$rc" != 0 ];grep -q 'COMPILED_WRONG_VARIANT' "$O/cmp_run$m.log";fi
 echo "compiled L2 m$m expected exit=$rc"
done
