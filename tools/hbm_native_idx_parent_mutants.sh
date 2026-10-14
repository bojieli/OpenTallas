#!/bin/bash
set -euo pipefail
base=$(realpath "$1");out=$(realpath -m "$2")
mkdir "$out"
bin="$base/obj/Vtb_hbm_idx_parent_owned_native"
for mut in LANE GID KEEP SVAL QORD;do
 d="$out/$mut";mkdir "$d"
 cp "$base/vectors/"{expected.json,frames.txt,keep.mem,lines.mem,qblk.mem} "$d/"
 if [ "$mut" = GID ];then
  # Observer-only expected-fault flag never enters DUT. Stop after actual
  # identity fault instead of spending200kcycles waiting forbidden completion.
  # Golden expected.json remains unchanged and frame0 must substantively fail.
  python3 - "$d/frames.txt" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text().splitlines();w=s[1].split();w[7]='1';s[1]=' '.join(w);p.write_text('\n'.join(s)+'\n')
PY
 fi
 (cd "$d" && "$bin" +MUT_"$mut") > "$d/run.log" 2>&1
 set +e
 python3 tools/hbm_idx_die_bench.py compare --work "$d" > "$d/verdict.log"
 rc=$?
 set -e
 [ "$rc" = 1 ]
 python3 - "$d/verdict.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));assert r['verdict']=='FAIL';assert any(not f['ok'] and f['why']!=['frame not run'] for f in r['frames'])
PY
 grep 'HBMIDX_FRAME' "$d/run.log"
 echo "NATIVE_PARENT_MUTANT $mut detected"
done
sha256sum "$bin" > "$out/binary.sha256"
