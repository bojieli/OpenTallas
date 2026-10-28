#!/usr/bin/env bash
# Scope-only AP runner. Source/canary/plan release is owned by ROOT/AP, never bypassed here.
set -euo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-grt}; MEM=${3:-24}; CPUS=${4:-8}
case "$GOAL" in cts|grt) ;; *) echo 'Rawleaf reviewed-placement runner permits cts/grt only' >&2; exit 2;; esac
python3 - "$K" <<'PY'
import hashlib,json,sys
from pathlib import Path
k=Path(sys.argv[1]);m=json.load(open(k/'RAWLEAF_RESUME.json'))
for n,e in [(m['placement'],m['placement_sha256']),(m['placement'].replace('.odb','.sdc'),m['sdc_sha256'])]:
 if hashlib.sha256((k/n).read_bytes()).hexdigest()!=e:raise SystemExit('reviewed placement/SDC changed: '+n)
for n,e in m['static_inputs_sha256'].items():
 if hashlib.sha256((k/n).read_bytes()).hexdigest()!=e:raise SystemExit('static source changed; restage after source gates: '+n)
PY
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}; DOCKER=${OT_DOCKER:-docker}; NAME=rawleaf-rst145-${GOAL}-$$
# -o marks the reviewed placement/SDC as intentional resume inputs. Make cannot re-place them.
"$DOCKER" run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 exec make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES='"$CPUS"' \
 -o /work/run/results/asap7/kq_ot_qwen_tile_lsl_rawfault_m3_a0k/base/3_place.odb \
 -o /work/run/results/asap7/kq_ot_qwen_tile_lsl_rawfault_m3_a0k/base/3_place.sdc '"$GOAL" \
 > "$K/run_${GOAL}_rst145.log" 2>&1
