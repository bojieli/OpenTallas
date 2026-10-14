#!/bin/bash
# Routed-top gate of the S81 SU slab (composition gate s81su_tiles; tools/s81_suhc/su_tile_tops.py):
#   su_tiles_gate.sh OUT exact   [FP]       the slab with every engine core replaced by its ROUTED top dsfd_su_t_<x>,
#                                           full shape, bit-exact; prints "RUN full_<FP>_m0_a0_h_t0 pass"
#   su_tiles_gate.sh OUT mutants [FP] [NPAR] one output mutant per routed-top class (+tmut=K) on the binary of OUT
#                                           (built by `exact` first, or here); prints one line per class and then
#                                           "SU_TILES_MUTANTS all <N> fail" (exit 1 = every mutant failed with error
#                                           rows, the expected result) or "SU_TILES_MUTANTS SURVIVOR <class> ..." (exit 0)
# FP = dpi (default; float primitives as DPI models, ~64 GB, minutes) or rtl (the routed float primitives fastfp / fp32_f12 /
# mul_lat / add_lat / prefix / add_l6 in RTL: ~384 GB and ~2.5 h of C++ build; the record of a tile that holds float
# primitives needs this one: results/rtl/ref_tile/s81su_tiles_gate_<sha>/qualification.json).
# Cases: /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl (ot-epyc1tb, ot-epyc4), as gate s81su_full.
set -u
O=$1; MODE=$2; FP=${3:-dpi}; NPAR=${4:-8}; R=$(cd "$(dirname "$0")/../.." && pwd); cd "$R"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
CASES=${SU_CASES:-/srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl}
mkdir -p "$O"
if [ ! -e "$O/runs.json" ]; then python3 tools/s81_suhc/su_gate.py prep --cases "$CASES" --out "$O" --shape full > "$O/prep.log" 2>&1 || { tail -5 "$O/prep.log"; exit 3; }; fi
if [ "$MODE" = exact ] || [ ! -e "$O/tile_tops/tile_tops.json" ]; then
  python3 tools/s81_suhc/su_gate.py run --out "$O" --shape full --hier --tiles --fp "$FP" > "$O/t0.log" 2>&1; rc=$?
  grep -h "SU_TILE_TOPS_[A-Z]\|PASS\|FAIL\|^RUN" "$O/t0.log"
  [ "$MODE" = exact ] && exit $rc
  grep -q "^RUN .* pass" "$O/t0.log" || { echo "SU_TILES_MUTANTS not run: the exact case does not pass"; exit 0; }
fi
N=$(python3 -c "import json;print(len(json.load(open('$O/tile_tops/tile_tops.json'))['tmut']))")
for k in $(seq 1 "$N"); do
  ( M=$O/tm_$k; mkdir -p "$M"; cp -al "$O/runs" "$M/runs" 2>/dev/null; cp "$O/runs.json" "$M/"; cp -a "$O/tile_tops" "$M/"
    for b in "$O"/build_*; do ln -sfn "$b" "$M/$(basename "$b")"; done
    python3 tools/s81_suhc/su_gate.py run --out "$M" --shape full --hier --tiles --fp "$FP" --tmut "$k" > "$O/t$k.log" 2>&1 ) &
  while [ "$(jobs -r | wc -l)" -ge "$NPAR" ]; do wait -n; done
done; wait
python3 - "$O" "$FP" <<'PY'
import json, sys, glob, re
o, fp = sys.argv[1], sys.argv[2]
tm = json.load(open(o + "/tile_tops/tile_tops.json"))["tmut"]; bad = []
for cls, k in sorted(tm.items(), key=lambda kv: kv[1]):
    f = glob.glob(f"{o}/tm_{k}/run_*_t{k}.json")
    d = json.load(open(f[0])) if f else None
    ok = bool(d and d["status"] == "fail" and all(x["err_rows"] > 0 for x in d["runs"]))
    print(f"SU_TILES_MUTANT {k} {cls} {'fail' if ok else 'SURVIVES'} err_rows {[x['err_rows'] for x in d['runs']] if d else None}")
    if not ok: bad.append(cls)
if bad:
    print("SU_TILES_MUTANTS SURVIVOR " + " ".join(bad)); sys.exit(0)
print(f"SU_TILES_MUTANTS all {len(tm)} fail"); sys.exit(1)
PY
