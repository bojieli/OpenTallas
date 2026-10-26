#!/bin/bash
set -euo pipefail
profile_dir=$(cd "$(dirname "$0")" && pwd -P)
mkdir -p "$profile_dir/output"
docker run --rm --memory=4g --memory-swap=4g --cpus=2 \
  -v "$profile_dir/kit:/work:ro" -v "$profile_dir/scripts:/scripts:ro" -v "$profile_dir/output:/out:rw" \
  openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit -threads 2 \
  /scripts/build_e5_upper_profile.tcl > "$profile_dir/output/profile.log" 2>&1
