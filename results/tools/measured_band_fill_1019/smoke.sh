#!/usr/bin/env bash
set -euo pipefail
for tag in floorplan placed cts; do
  printf 'read_db /work/%s.odb\nsource /work/layout_dump.tcl\nexit\n' "$tag" > "$tag.tcl"
  docker run --rm -e OT_LAYOUT_OUT="/work/$tag.json" -v "$PWD:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/work/$tag.tcl" > "$tag.log" 2>&1
  test -s "$tag.json"
  sha256sum "$tag.odb" "$tag.json"
done
printf 'OCCUPANCY_SMOKE_PASS\n'
