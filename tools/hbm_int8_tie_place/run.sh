#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 tools/hbm_int8_tie_place/import_json.py safe_mapped.json netlist.v
docker image inspect openroad/orfs:asap7lock --format '{{.Id}}' > image.sha
sha256sum safe_mapped.json netlist.v die_constant_cells.tcl pdn.tcl > INPUT_SHA256SUMS
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/tools/hbm_int8_tie_place/place.tcl > place.log 2>&1
for name in before after_ties placed; do
 docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/export_raw.py "/work/$name.odb" "/work/$name"
done
