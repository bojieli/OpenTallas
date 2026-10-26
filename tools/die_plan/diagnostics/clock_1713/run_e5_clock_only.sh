#!/bin/bash
set -euo pipefail
diag_dir=$(cd "$(dirname "$0")" && pwd -P)
mkdir -p "$diag_dir/output"
cd "$diag_dir"
sha256sum --status -c input.sha256
docker run --rm --memory=32g --memory-swap=32g --cpus=8 \
  -v "$diag_dir/kit:/work:ro" -v "$diag_dir/scripts:/scripts:ro" -v "$diag_dir/output:/out:rw" \
  openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit -threads 8 /scripts/e5_clock_only.tcl' \
  > output/route.log 2>&1
for corner in TT FF; do
  docker run --rm --memory=8g --memory-swap=8g --cpus=2 -e CLOCK_CORNER="$corner" \
    -v "$diag_dir/kit:/work:ro" -v "$diag_dir/scripts:/scripts:ro" -v "$diag_dir/output:/out:rw" \
    openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit -threads 2 /scripts/e5_clock_measure.tcl' \
    > "output/measure_${corner}.log" 2>&1
done
sha256sum --status -c input.sha256
