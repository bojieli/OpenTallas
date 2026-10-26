#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
for mode in q_rq q_zero p_zero;do
 mkdir -p "$out/$mode"
 python3 - "$mode" "$out/$mode/dut.sv" <<'PY'
from pathlib import Path
import sys
mode,out=sys.argv[1:];kind='p' if mode.startswith('p') else 'query';s=Path(f'rtl/hdc/v41x/static/ot_hbm_attn_{kind}_prefetch_h1.sv').read_text()
if mode=='q_rq':
 a="rq[k*17+:17]<={fetch_v&&fetch_head==0";b="rq[k*17+:17]<={fetch_v"
else:
 a='.write_v(vp[FILL_LAT-1])';b='.write_v(vp[FILL_LAT-1]&&ap[FILL_LAT-1])'
assert s.count(a)==1,(mode,a);Path(out).write_text(s.replace(a,b))
PY
 set +e
 if [ "$mode" = p_zero ];then P_H1_RTL="$out/$mode/dut.sv" bash tools/hbm_static_attention/run_h1_prefetch.sh "$out/$mode/gate" > "$out/$mode/runner.log" 2>&1;else Q_H1_RTL="$out/$mode/dut.sv" bash tools/hbm_static_attention/run_h1_prefetch.sh "$out/$mode/gate" > "$out/$mode/runner.log" 2>&1;fi
 rc=$?;set -e;echo "$rc" > "$out/$mode/runner.rc"
 if [ "$rc" = 0 ];then echo "FAIL H1 actualDUT mutant survived $mode";exit 1;fi
 grep -qE 'H1_PREFETCH (inactive query VM request|query zero/data mismatch|P zero/data mismatch)' "$out/$mode/gate/seed41.log"
done
echo 'PASS three actualH1RTL DUT mutants rejected: unwanted inactive VM requests and missing query/P realzero SRAM writes' > "$out/gate"
