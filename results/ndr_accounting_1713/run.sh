#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")" && pwd)
docker run --rm --cpus=1 --memory=2g --memory-swap=2g -v "$R":/out openroad/orfs:asap7lock bash -lc 'set -e; cd /out; g++ --version | head -1; g++ -std=c++17 -O2 accounting.cpp -o accounting; ./accounting 15 > accounting.log; g++ -std=c++17 -O2 -fsanitize=float-cast-overflow -fno-sanitize-recover=float-cast-overflow accounting.cpp -o accounting_ubsan; set +e; ./accounting_ubsan 15 bad-only > ubsan.log 2>&1; status=$?; echo "$status" > ubsan.exit; test "$status" -ne 0; grep -q "outside the range" ubsan.log'
python3 - "$R" <<'CHECK'
from pathlib import Path
import re,sys,json
r=Path(sys.argv[1]);text=(r/'accounting.log').read_text();rows={}
for label,signed,stored in re.findall(r'RESULT (\S+) signed_before_conversion=(-?[0-9.]+) stored_usage=(\d+)',text):rows[label]={'signed_before_conversion':float(signed),'stored_usage':int(stored)}
assert rows['heterogeneous']=={'signed_before_conversion':-180.0,'stored_usage':65356},rows
assert rows['same_cost_negative_delta_safe']['signed_before_conversion']>=0,rows
assert rows['heterogeneous_reverse_remove_safe']['signed_before_conversion']==15.0,rows
assert rows['positive_control']['stored_usage']==65356,rows
(r/'summary.json').write_text(json.dumps({'model_results':rows,'ubsan_exit':int((r/'ubsan.exit').read_text()),'actual_e5_trigger':'UNPROVEN: requires actual per-operation trace; synthetic candidate only'},indent=2)+'\n')
print('ACCOUNTING_REPRO_PASS; negative delta alone safe; heterogeneous order can go negative; observed number ambiguous without trace')
CHECK
