#!/bin/bash
# CORE-HBM-SPLIT (2026-10-23): RTL top of a REMAINDER split piece (master minus member instances), extracted by yosys
# from the master twin RTL: hierarchy (params) -> proc -> keep_hierarchy on the member module types -> flatten ->
# submod of every cell except the excluded members -> write_verilog of that submodule (word-level, synthesizable;
# kept hierarchical cells and SRAM macros stay instances of their RTL / macro modules).
#   rest_extract.sh <repo> <out dir> <name> <master top> <keep mods comma> <exclude cell glob(s) comma> [MEMG]
#   env FILES=<list> (as elab_check.sh; else master_filelist.py on the master top), PARAMS=k=v,...
# Writes <out>/<name>.v (module <name>), <name>.ports (dir width name), <name>.log.
set -u
SRC=$(readlink -f $1); OUT=$(readlink -f $2); NAME=$3; TOP=$4; KEEP=$5; EXCL=$6; MEMG=${7:-16}
mkdir -p $OUT
if [ -n "${FILES:-}" ]; then python3 - $FILES $TOP > $OUT/$NAME.files.json <<'PY0'
import json, sys
L = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
mac = [l[6:] for l in L if l.startswith('macro:')]
print(json.dumps({"top": sys.argv[2], "files": [l for l in L if not l.startswith('macro:')],
                  "macros": [{"module": m, "file": f"physical/asap7_memory_macros_v2/{m}/{m}_bb.v"} for m in mac]}))
PY0
else
  HDIE_ALLOW_AMBIGUOUS=1 python3 $SRC/tools/hbm_die_v15/master_filelist.py $TOP --root $SRC --json > $OUT/$NAME.files.json || { echo "$NAME FILELIST_FAIL"; exit 2; }
fi
python3 - $OUT/$NAME.files.json $OUT/$NAME.ys $TOP "$KEEP" "$EXCL" $NAME <<'PY'
import json, sys, os
d = json.load(open(sys.argv[1])); top, keep, excl, name = sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
for f in [x for x in os.environ.get('EXTRA', '').split(',') if x]:   # files the walker misses (define-gated children)
    if f.startswith('macro:'):
        mm = f[6:]
        if all(x['module'] != mm for x in d.get('macros', [])):
            d.setdefault('macros', []).append({'module': mm, 'file': f'physical/asap7_memory_macros_v2/{mm}/{mm}_bb.v'})
    elif f not in d['files']:
        d['files'].append(f)
json.dump(d, open(sys.argv[1], 'w'), indent=1)
dfs = ''.join(f' -D{x}' for x in os.environ.get('DEFINES', '').split(',') if x)
L = [f"read_verilog -lib {m['file']}" for m in d.get('macros', [])]
L += [f"read_verilog -sv -DSYNTHESIS{dfs} {f}" for f in d['files']]
for kv in [x for x in os.environ.get('PARAMS', '').split(',') if x]:
    k, v = kv.split('='); L.append(f"chparam -set {k} {v} {top}")
L += [f"hierarchy -check -top {top}", "rename -top elab_top", "proc", "opt_clean"]
for k in [x for x in keep.split(',') if x]:
    L.append(f"setattr -mod -set keep_hierarchy 1 {k} $paramod*\\\\{k}*")
L += ["flatten", "opt_clean", "splitnets", "opt_clean", "cd elab_top"]   # bit-exact boundary
sel = ' '.join(x for x in excl.split(',') if x)
L += [f"select -set ex {sel}", "tee -o /out/%s.excl select -list @ex" % name,
      f"submod -name {name} c:* @ex %d", "cd ..", f"select {name}",
      f"write_verilog -selected -noattr /out/{name}.v", "select elab_top", f"write_verilog -selected -noattr /out/{name}.parent.v"]
open(sys.argv[2], 'w').write("\n".join(L) + "\n")
PY
docker run --rm --name split-rest-$NAME-$$ --cpus=4 --memory=${MEMG}g -v $SRC:/src:ro -v $OUT:/out -w /src openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /out/$NAME.log -s /out/$NAME.ys" >/dev/null 2>&1
rc=$?
python3 - $OUT/$NAME.v $NAME > $OUT/$NAME.ports <<'PY'
import re, sys
txt = open(sys.argv[1]).read() if __import__('os').path.exists(sys.argv[1]) else ''
m = re.search(r'(?ms)^module\s+\\?' + re.escape(sys.argv[2]) + r'\b.*?^endmodule', txt)
for l in (m.group(0).splitlines() if m else []):
    mm = re.match(r'  (input|output|inout)\s+(?:signed\s+)?(?:\[(\d+):(\d+)\]\s*)?(\S+?)\s*;', l)   # module level only
    if mm:
        w = abs(int(mm.group(2)) - int(mm.group(3))) + 1 if mm.group(2) else 1
        print(mm.group(1), w, mm.group(4).lstrip('\\'))
PY
i=$(awk '$1=="input"{s+=$2}END{print s+0}' $OUT/$NAME.ports); o=$(awk '$1=="output"{s+=$2}END{print s+0}' $OUT/$NAME.ports)
echo "$NAME rc=$rc inp=$i out=$o excluded_cells=$(wc -l < $OUT/$NAME.excl 2>/dev/null)"
