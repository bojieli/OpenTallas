#!/bin/bash
set -euo pipefail
diag_dir=$(cd "$(dirname "$0")" && pwd -P)
docker run --rm --memory=4g --memory-swap=4g --cpus=2 \
  -v "$diag_dir/kit:/work:ro" -v "$diag_dir/scripts:/scripts:ro" \
  -v "$diag_dir/output:/out:rw" \
  -e CLOCK_ODB=/work/checkpoint/4_cts.odb \
  -e MACRO_IF_TSV=/work/f6_placed_complete.tsv \
  -e CLOCK_INVENTORY_OUT=/out/clock_inventory.json \
  openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad \
  -no_init -python -exit /scripts/e5_clock_inventory.py > "$diag_dir/output/inventory.log" 2>&1
