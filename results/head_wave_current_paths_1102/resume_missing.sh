#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
python3 - "$D" <<'PY'
from pathlib import Path
import sys,json,hashlib
D=Path(sys.argv[1]);s=json.load(open(D/'SOURCE.json'));r=json.load(open(D/'LOOK_RELEASE.json'))
assert r['personally_viewed'] is True and r['source']==s
for n,files in s.items():
 for f,h in files.items():assert hashlib.sha256((D/n/f).read_bytes()).hexdigest()==h,(n,f)
PY
for n in hd_spn_eshim_tx hd_st_n3_turn; do
 for c in TT FF; do
  if [ "$n/$c" = hd_spn_eshim_tx/TT ]; then
   python3 - "$D/$n/query_TT.log" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
assert 'QUERY exact recorded native library/config digests matched' in s
assert 'CURRENT_PATHS_END MAX' in s and 'CURRENT_PATHS_END MIN' in s
assert 'setup_est -46.51 hold_est -80.73' in s
PY
   echo 'SKIP existing complete Eshim TT paths; post-report unsupported diagnostic preserved'
   continue
  fi
  test ! -f "$D/$n/query_$c.log" || { echo "refuse duplicate $n/$c"; exit 2; }
  docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$D/$n":/work -v "$D/$n/native":/work/native:ro -e OT_POSTCTS_GRT=1 -e OT_CORNER="$c" -e ODB=/work/native/5_1_grt.odb openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /work/verify_context.py; openroad -threads 2 -exit /work/path_query.tcl' > "$D/$n/query_$c.log" 2>&1
 done
done
echo 'READONLY missing3corners collected; firstTTdata preserved; no repair/route/adoption'
