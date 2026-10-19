#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p packet
for name in before after_ties placed; do
 gzip -c "$name/raw.json" > "packet/${name}_raw.json.gz"
 cp "$name/SHA256SUMS" "packet/${name}_SHA256SUMS"
done
cp audit_after_ties/summary.json packet/after_ties_summary.json
cp audit_placed/summary.json packet/placed_summary.json
cp audit_after_ties/census.json.gz packet/after_ties_census.json.gz
cp audit_placed/census.json.gz packet/placed_census.json.gz
sha256sum *.odb safe_mapped.json tools/hbm_int8_tie_place/*.py tools/hbm_int8_tie_place/*.sh tools/hbm_int8_tie_place/*.tcl tools/dft/*.py > packet/ALL_SOURCE_SHA256SUMS
