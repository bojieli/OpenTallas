#!/bin/bash
set -euo pipefail
R=${1:?regions}; W=${2:?new output path}
cd "${SRC:-.}"
python3 tools/s81/prepare_pq_return_delay_eco.py --regions "$R" --out "$W"
IB=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["input_base"])' "$W/preparation.json")
IMG=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["image_id"])' "$W/preparation.json")
TAG=$(docker image inspect openroad/orfs:asap7lock --format '{{.Id}}')
[ "$TAG" = "$IMG" ] || { echo 'Signoff image differs from pinned runtime image'; exit 1; }
docker run --rm "$IMG" bash -lc 'cd /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM && sha256sum asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib' > "$W/library_sha256.txt"
python3 - "$W/library_sha256.txt" <<'PYCODE'
import json,sys
expected=json.load(open('physical/s81_pq_return_delay/library_binding.json'))
actual={line.split()[1]:line.split()[0] for line in open(sys.argv[1])}
if actual != expected: raise SystemExit('Actual SS/FF libraries differ from modeled chain characterization')
PYCODE
EB=$W/orfs/results/asap7/pq_return_delay/base
mkdir -p "$EB"
cp "$IB/6_final.sdc" "$EB/6_final.sdc"
docker run --rm -v "$IB:/in:ro" -v "$W:/p" -v "$PWD:/src:ro" \
 -e OT_CORNER=ff -e OT_DB=/in/6_final.odb -e OT_SDC=/in/6_final.sdc -e OT_SPEF=/in/6_final.spef \
 -e OT_POST_SDC=/src/physical/s81_pq_return_delay/signoff.sdc -e OT_EFF=/p/eff_ff.sdc \
 "$IMG" bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/physical/s81_pq_return_delay/frozen/hold_eco_corner.tcl' > "$W/corner_pre_ff.log" 2>&1
grep -q 'OT_CORNER_EFF done' "$W/corner_pre_ff.log"
docker run --rm -v "$IB:/in:ro" -v "$W:/p" -v "$PWD:/src:ro" \
 -e OT_DB=/in/6_final.odb -e OT_SDC=/p/eff_ff.sdc -e OT_PRE_SPEF=/in/6_final.spef \
 -e OT_OUT=/p/orfs/results/asap7/pq_return_delay/base -e OT_SESSION=ff -e OT_THREADS=16 \
 -e OT_CL=/src/physical/s81_pq_return_delay/frozen -e OT_ALLOW_FRESH_GRT=1 \
 "$IMG" bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /p/explicit_eco.tcl' > "$W/eco.log" 2>&1
grep -q 'PQ_DELAY_ROUTE_DONE' "$W/eco.log"
python3 tools/w18/corner_sta.py --orfs-dir "$W/orfs" --post-sdc physical/s81_pq_return_delay/signoff.sdc --output "$W/corner_sta.json" > "$W/signoff.log" 2>&1
python3 tools/s81/check_pq_return_delay_result.py --work "$W"
