#!/bin/bash
# CORE-HBM-SPLIT (2026-10-23): elaborate one split-piece RTL top (yosys hierarchy -check, no synthesis) in the ORFS
# image and print its port list.  elab_check.sh <repo root> <out dir> <top> [MEMG]
#   <out>/<top>.files.json (master_filelist.py), <top>.ys, <top>.log, <top>.ports (dir width name), <top>.resize (port
#   width mismatches at any instance: must be empty)
set -u
SRC=$(readlink -f $1); OUT=$(readlink -f $2); TOP=$3; MEMG=${4:-8}; NAME=${NAME:-$TOP}; export NAME
mkdir -p $OUT
if [ -n "${FILES:-}" ]; then python3 -c "import json,sys; print(json.dumps({\"top\": sys.argv[2], \"files\": [l.strip() for l in open(sys.argv[1]) if l.strip()], \"macros\": []}))" $FILES $TOP > $OUT/$NAME.files.json; else
  HDIE_ALLOW_AMBIGUOUS=1 python3 $SRC/tools/hbm_die_v15/master_filelist.py $TOP --root $SRC --json > $OUT/$NAME.files.json || { echo "$TOP FILELIST_FAIL"; exit 2; }; fi
python3 - $OUT/$NAME.files.json $OUT/$NAME.ys $TOP <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); top = sys.argv[3]
if d.get('unresolved'):
    print('UNRESOLVED', d['unresolved'])
L = [f"read_verilog -lib {m['file']}" for m in d.get('macros', [])]
L += [f"read_verilog -sv -DSYNTHESIS {f}" for f in d['files']]
import os
for kv in [x for x in os.environ.get('PARAMS', '').split(',') if x]:
    k, v = kv.split('=')
    L.append(f"chparam -set {k} {v} {top}")
L += [f"hierarchy -check -top {top}", f"cd {top}", "delete p:* c:*", "cd ..", f"select {top}",
      f"write_verilog -selected -noexpr /out/{os.environ.get('NAME', top)}.ports.v"]
open(sys.argv[2], 'w').write("\n".join(L) + "\n")
PY
docker run --rm --name split-elab-$NAME-$$ --cpus=2 --memory=${MEMG}g -v $SRC:/src:ro -v $OUT:/out -w /src openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /out/$NAME.log -s /out/$NAME.ys" >/dev/null 2>&1
rc=$?
grep -i "resizing cell port" $OUT/$NAME.log > $OUT/$NAME.resize
python3 - $OUT/$NAME.ports.v > $OUT/$NAME.ports <<'PY'
import re, sys
for l in open(sys.argv[1]):
    m = re.match(r'\s*(input|output|inout)\s+(?:signed\s+)?(?:\[(\d+):(\d+)\]\s*)?(\S+?)\s*;', l)
    if m:
        w = abs(int(m.group(2)) - int(m.group(3))) + 1 if m.group(2) else 1
        print(m.group(1), w, m.group(4).lstrip('\\'))
PY
i=$(awk '$1=="input"{s+=$2}END{print s+0}' $OUT/$NAME.ports); o=$(awk '$1=="output"{s+=$2}END{print s+0}' $OUT/$NAME.ports)
echo "$NAME rc=$rc inp=$i out=$o resize=$(wc -l < $OUT/$NAME.resize)"
