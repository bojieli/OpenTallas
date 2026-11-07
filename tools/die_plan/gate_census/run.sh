#!/bin/bash
# Census of gates outside their real fanin+fanout box on a placed DB: run.sh ODB OUTDIR. Read-only, 16 GB cap, about 2 minutes.
set -euo pipefail
cd /
ODB=$(readlink -f "$1"); OUT=$2; HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$OUT"; OUT=$(readlink -f "$OUT"); cp "$HERE/census.tcl" "$OUT/census.tcl"
docker run --rm -m 16g -v /srv:/srv -v "$OUT":"$OUT" -v "$(dirname "$ODB")":"$(dirname "$ODB")" -e ODB="$ODB" -e OT_OUT="$OUT/census.tsv" \
  openroad/orfs:asap7lock bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit $OUT/census.tcl" > "$OUT/census.log" 2>&1
python3 -I "$HERE/gate_rehome.py" "$OUT/census.tsv" --report-only
