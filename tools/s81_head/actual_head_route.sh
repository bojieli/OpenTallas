#!/bin/bash
# Resume only a qualified, repaired GRT checkpoint, without rebuilding CTS/GRT.
set -euo pipefail
K=$(realpath "$1")
MEM=${2:-48}
CPUS=${3:-16}
python3 - "$K" <<'PY'
import json, sys
from pathlib import Path
k=Path(sys.argv[1])
tt=json.loads((k/'actual_sta_TT.json').read_text())
ff=json.loads((k/'actual_sta_FF.json').read_text())
lec=json.loads((k/'lec_actual_r2/lec.json').read_text())
assert tt['setup_ps'] >= 0 and tt['setup_endpoints'] == 0, tt
assert ff['hold_ps'] >= 0 and ff['hold_endpoints'] == 0, ff
assert lec['verdict'] == 'EQUIVALENT', lec.get('verdict')
PY
# Repair used FF-vclk202.5. Normal routing/final output carries the TT250 source
# contract; signoff separately binds FF202.5, with the source offset fixed at0.
BASE=$(find "$K/run/results/asap7" -name 5_1_grt.odb -printf '%h\n')
test -n "$BASE"
cp "$BASE/5_1_grt.sdc" "$K/repaired_FF_5_1_grt.sdc"
cp "$K/constraint.sdc" "$BASE/5_1_grt.sdc"
docker run --rm --memory="${MEM}g" --memory-swap="${MEM}g" --cpus="$CPUS" \
  -v "$K":/work -e CPUS="$CPUS" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
    M=(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$CPUS" CORNER=TC "CORNERS=tc bc")
    "${M[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc
    "${M[@]}" do-finish
    "${M[@]}" do-generate_abstract
  ' > "$K/actual_route.log" 2>&1
python3 -I "$K/signoff.py" run --kit "$K" --run-dir "$K/run" --corners tt,ff \
  --ff-vclk bound-ff --ff-bound-ps 202.5 \
  --ff-vclk-contract 'HEAD actual standalone clock contract: actual_contract.json; primary ft_mstrap_i; zero source offset' \
  --docker docker --image openroad/orfs:asap7lock --out "$K/signoff_actual" > "$K/signoff_actual.log" 2>&1
