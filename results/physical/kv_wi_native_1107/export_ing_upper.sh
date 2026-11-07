#!/bin/bash
set -eu
R=$(cd "$(dirname "$0")" && pwd)
K=$R/source
test ! -e "$R/detail.lef"
python3 -I "$R/abstract_detail.py" tcl --odb /source/6_final.odb --out /out/detail.lef --bloat-factor 0 > "$R/export.tcl"
docker run --rm --cpus=2 --memory=12g --memory-swap=12g -v "$K/run/results/asap7/hc_qkd_hr_ingest_eng__362_88x362_88/base:/source:ro" -v "$R:/out" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/export.tcl' > "$R/export.log" 2>&1
python3 -I "$R/abstract_detail.py" splice --base "$K/views/qkd_hr_ingest_eng.lef" --detail "$R/detail.lef" --out "$R/qkd_hr_ingest_eng.lef" --layers M6,M7 > "$R/splice.json"
python3 -I "$R/abstract_detail.py" check --base "$K/views/qkd_hr_ingest_eng.lef" --new "$R/qkd_hr_ingest_eng.lef" --layers M6,M7 > "$R/check.json"
