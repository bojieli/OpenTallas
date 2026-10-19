#!/usr/bin/env bash
# Run on the fleet only, after the preserved TP4 full36 gold finishes.
# This script is a TP4 reference diagnostic, not the release TP8 RTL token gate.
# Arguments are deliberately rejected; the old l3seed script ignored them.
set -eu
[ "$#" -eq 0 ] || { echo 'Use explicit QW_FULL36_* environment settings; no positional arguments.' >&2; exit 2; }
B=${QW_FULL36_BASE:-/srv/opentallas-scratch/claude/tokpass-qwen-1018}
O=${QW_FULL36_OUT:-/srv/opentallas-scratch/claude/mu-qw-die/b5/full36_tp4_diagnostic}
H=${QW_FULL36_HISTORY:-$B/fx/history_full36}
PY=${QW_FULL36_PYTHON:-/usr/bin/python3.14}
[ ! -e "$O" ] || { echo "Preserve existing output: $O" >&2; exit 2; }
grep -q 'gold rc=0' "$B/STATUS.log" || { echo 'Preserved full36 gold has not completed successfully.' >&2; exit 2; }
cd "$B/src"
# Inspect the actual oracle instead of accepting an L3 or L0/L1 fixture by name.
"$PY" - "$B/fx/gold/tp4/oracle.json" <<'PY'
import json, sys
a = json.load(open(sys.argv[1]))
assert a.get('layers') == 36, 'requires 36-layer oracle'
assert a.get('tp') == 4, 'this diagnostic is TP4 only'
p = a['per_position']['8191']
assert 'head' in p, 'requires final-layer/head golden'
assert len(p['kv_pre_sha256']) == 144, 'requires all layer/die histories'
PY
"$PY" tools/exactness/fixtures.py history --gold "$B/fx/gold/tp4/P8191" --out "$H"
mkdir -p "$O"
printf 'TP4_REFERENCE_DIAGNOSTIC_ONLY; release TP8 requires its own matching arithmetic, full36/head fixtures and RTL token evidence.\n' > "$O/SCOPE.txt"
sha256sum "$B/fx/gold/tp4/oracle.json" tools/qwen_hbmacc_position_oracle_gpu.py > "$O/source.sha256"
export PYTHONPATH="$B/pylib" QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 OMP_NUM_THREADS=16
"$PY" tools/qwen_hbmacc_position_oracle_gpu.py --run --device cpu \
  --prep-dir "$B/fx/prep/tp4" --layers 36 --head \
  --tokens "$B/fx/inputs/prompt_tokens_8192.txt" --positions 8188,8189,8190 \
  --embedding-npz "$B/fx/inputs/prompt_embedding.npz" \
  --kv-history "$H" --out "$O" > "$O/run.log" 2>&1
