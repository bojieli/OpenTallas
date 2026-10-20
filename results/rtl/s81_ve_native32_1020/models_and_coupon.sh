#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p cell_models
VE_IMAGE=$(docker image inspect openroad/orfs:latest --format '{{.Id}}')
echo "$VE_IMAGE" > cell_models/image_id.txt
python3 - <<'INNER'
from pathlib import Path
rows=['read_liberty -ignore_miss_func /work/'+x+'.lib' for x in ['AO','INVBUF','OA','SEQ','SIMPLE']]
rows+=['proc','write_verilog -noattr /work/cell_models/imported.v']
Path('cell_models/models.ys').write_text('\n'.join(rows)+'\n')
INNER
docker run --rm --memory=8g --memory-swap=8g -v "$PWD:/work" -w /work "$VE_IMAGE" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -l cell_models/models_yosys.log -s cell_models/models.ys' > cell_models/models.stdout 2>&1
python3 canonical_seq_coupon.py --pdk-seq canonical_SEQ.v --pdk-sha256 6e63ff4b5587097a76bf395c6f2383035368d5c8d95dbf551ba324d3a9537fde --out cell_models/coupon --imported-model cell_models/imported.v > cell_models/coupon.log 2>&1
cat cell_models/coupon.log
