#!/bin/bash
set -euo pipefail
diag_dir=$(cd "$(dirname "$0")" && pwd -P)
mkdir -p "$diag_dir/output"
sha256sum -c "$diag_dir/input.sha256"
docker run --rm --memory=32g --memory-swap=32g --cpus=8 \
  -v "$diag_dir/kit:/work:ro" -v "$diag_dir/scripts:/scripts:ro" \
  -v "$diag_dir/output:/out:rw" -w /out openroad/orfs:asap7lock \
  bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit -threads 8 /scripts/e5_clock_m67.tcl' \
  > "$diag_dir/output/grt.log" 2>&1
sha256sum -c "$diag_dir/input.sha256"
