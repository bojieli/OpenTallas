#!/bin/bash
set -eu
K=$(cd "$1" && pwd); MEM=${2:-48}; CPUS=${3:-8}; T=$(basename "$K")
python3 - "$K" <<'PY'
import json,sys
from pathlib import Path
k=Path(sys.argv[1]);assert json.load(open(k/'lec/lec.json'))['verdict']=='EQUIVALENT';a=json.load(open(k/'union_resume.json'));assert a['delta'].startswith('cland_occupy proc only')
PY
python3 -I "$K/kit_preflight.py" "$K" --out "$K/union_preflight.json"
mapfile -t CKS < <(find "$K/run/results/asap7" -name 3_2_place_iop.odb)
[ ${#CKS[@]} = 1 ]; IOP=/work/${CKS[0]#"$K/"}; SDC="$(dirname "$IOP")/2_floorplan.sdc"
NAME=qc-union-$T-$$
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work -e CPUS="$CPUS" -e IOP="$IOP" -e SDC="$SDC" -e HUID="$(id -u)" -e HGID="$(id -g)" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$CPUS" -o "$IOP" -o "$SDC" place
 rc=$?
 chown -R "$HUID:$HGID" /work
 exit "$rc"
' > "$K/run_place_union.log" 2>&1
