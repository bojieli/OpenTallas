#!/bin/bash
# usage (inside ot-run, from the repo worktree root): tools/hbm_b2/q3sync/asm_sync_gate.sh <OUT> <legacy|sync>
# Elaboration gate for the actual five-core q3 producer assembly with the q3 SYNC_INPUT profile adopted.
# Rule 3: refuses a dirty tracked tree; inputs are repo-relative at HEAD; __q3sync copies + the adopted assembly are
# regenerated at HEAD into <OUT> (gen/, ot_hbm_q3_producer_native__q3sync.sv).
# LINT_FLAGS (default strict: -Werror-SELRANGE -Werror-WIDTH, which stops at the legacy HDC WIDTHTRUNC debt before full
# elaboration); LINT_FLAGS="-Werror-SELRANGE -Wno-WIDTH" elaborates the whole assembly.
set -u
OUT=$1; MODE=$2
WT=$(git rev-parse --show-toplevel) || exit 2
cd "$WT"
[ -n "$(git status --porcelain --untracked-files=no)" ] && { echo "DIRTY tracked tree: refuse"; exit 2; }
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
ASM=rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hbm_q3_producer_native.sv
CEN=tools/hbm_b2/q3sync/cohort.json
mkdir -p "$OUT"; git rev-parse HEAD > "$OUT/source_commit_$MODE.txt"
sha256sum -c tools/hbm_b2/q3sync/q3_producer_native.sha256 > "$OUT/asm_sha_$MODE.log" 2>&1 || { echo "ASM SHA FAIL"; exit 2; }
if [ $MODE = sync ]; then
  rm -rf "$OUT/gen"
  python3 -I tools/hbm_b2/q3sync/q3_sync_profile.py --root . --files tools/hbm_b2/q3sync/q3b.files --out "$OUT/gen" \
     --census "$OUT/census_regen.json" > "$OUT/gen.log" 2>&1 || { echo "GEN FAIL"; exit 2; }
  python3 -I tools/hbm_b2/q3sync/q3_assembly_sync.py --asm $ASM --census $CEN --gen "$OUT/gen" \
     --out "$OUT/ot_hbm_q3_producer_native__q3sync.sv" --report "$OUT/asm_sync.json" > "$OUT/asm_sync.log" 2>&1 \
     || { cat "$OUT/asm_sync.log"; exit 2; }
  files=$(python3 -c "
import json;c=json.load(open('$CEN'));s=[]
[s.append(f) for k in c['core_filelists'] for f in c['core_filelists'][k]['files'] if f not in s]
print(' '.join('$OUT/gen/'+f for f in s))")
  top=ot_hbm_q3_producer_native__q3sync; files="$OUT/ot_hbm_q3_producer_native__q3sync.sv $files"
  # no async event control may remain anywhere in the adopted closure
  python3 - "$OUT" $files > "$OUT/async_scan.json" <<'PY'
import sys, re, json
rx = re.compile(r"@\s*\(\s*(posedge|negedge)\s+[^)]*?(\bor\b|,)\s*(posedge|negedge)\b")
hits = {}
for f in sys.argv[2:]:
    t = re.sub(r"//[^\n]*|/\*.*?\*/", "", open(f).read(), flags=re.S)
    n = len(rx.findall(t))
    if n: hits[f] = n
print(json.dumps({"files": len(sys.argv) - 2, "async_event_controls": sum(hits.values()), "hits": hits}))
PY
else
  files=$(python3 -c "
import json;c=json.load(open('$CEN'));fl=set(f for k in c['core_filelists'] for f in c['core_filelists'][k]['files'])
s=[]
[s.append(e['source']) for e in c['emitted'] if e['emitted'] in fl and e['source'] not in s]
print(' '.join(s))")
  top=ot_hbm_q3_producer_native; files="$ASM $files"
fi
mac=$(python3 -c "
import json;c=json.load(open('$CEN'));s=[]
[s.append(m) for k in c['core_filelists'] for m in c['core_filelists'][k]['macros'] if m not in s]
print(' '.join(s))")
LF=${LINT_FLAGS:--Werror-SELRANGE -Werror-WIDTH}
log=$OUT/lint_$MODE.log
echo "# $(date) host=$(hostname) commit=$(git rev-parse HEAD) mode=$MODE top=$top" > $log
echo "# $V --lint-only -Wno-fatal $LF -Wno-TIMESCALEMOD --error-limit 1000000 --top-module $top <files> <macros>" >> $log
echo "# files: $(echo $files $mac | wc -w)" >> $log
/usr/bin/time -v $V --lint-only -Wno-fatal $LF -Wno-TIMESCALEMOD --error-limit 1000000 \
   --Mdir $OUT/obj_$MODE --top-module $top $files $mac >> $log 2>&1
echo "# rc=$? $(date)" >> $log
rm -rf $OUT/obj_$MODE
tail -1 $log
