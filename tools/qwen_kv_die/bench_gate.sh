#!/bin/bash
# qwen-1010/b 2026-10-10: closure-loop bench gate for a re-cut H source (the stack RTL in this tree), run from the source
# root.  pos: the layer-step campaign (rtl/test/qwen_kv_die/bench_run.sh STACK=h, typical PHY: 28 1 7 5 29 28 34), base
# build only, 7 vectors x VM stall 0 / 1 -> exit 0 iff all 14 runs are bit-exact.  neg <MUT>: the same harness built
# with -GMUT=<MUT> (a known-inexact mutant), run on 8192_normal -> exit 0 iff exact (so the gate expects FAIL).
#   bench_gate.sh pos OUT          bench_gate.sh neg OUT [MUT=2]
set -u
MODE=$1; OUT=$2; MUT=${3:-2}
SRC=$(pwd)
mkdir -p "$OUT"
if [ "$MODE" = pos ]; then
  STACK=h bash rtl/test/qwen_kv_die/bench_run.sh "$SRC" "$OUT" 28 1 7 5 29 28 34 0 || exit 3
  python3 - "$OUT/results.jsonl" <<'PY'
import json, sys
rows = [json.loads(x) for x in open(sys.argv[1]) if x.strip()]
base = [r for r in rows if r['run'] == 'base']
ok = len(base) == 14 and all(r['rc'] == 0 and r['res'] and r['res']['exact'] for r in base)
steps = {r['vec']: r['res']['marks']['res_last_at_vm'] - r['res']['marks']['ctl_sent'] for r in base if r['res']}
print(json.dumps(dict(runs=len(base), exact_all=ok, step=steps)))
sys.exit(0 if ok else 1)
PY
  exit $?
fi
V=$OUT/v/8192_normal
mkdir -p "$OUT/log"
python3 tools/qwen_nearhbm_attn_ref.py vectors --ctx 8192 --seed $((8192*7+6)) --kind normal --out "$V" > "$OUT/log/vec.log" 2>&1 || exit 3
STACK=h bash rtl/test/qwen_kv_die/build_qkvd_tb.sh "$OUT/bm" -GR=8 -GLINK=7 -GROM_ST=28 -GKV_ST=1 -GPHY_LAT=5 -GQX=29 -GRX=28 -GKVL=34 \
  -GMUT=$MUT > "$OUT/log/build.log" 2>&1 || exit 3
r=$("$OUT/bm/Vtb" "$V" 0 2> "$OUT/log/mut.err"); rc=$?
echo "{\"run\": \"mut$MUT\", \"rc\": $rc, \"res\": ${r:-null}}" | tee "$OUT/mut.json"
python3 -c "import json,sys; d=json.load(open('$OUT/mut.json')); sys.exit(0 if d['res'] and d['res']['exact'] else 1)"
