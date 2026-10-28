#!/bin/bash
# Run the three STA views written by `ohier sta-scripts` (flat, stitched, etm) in the ORFS image
# with standalone OpenSTA (no LEF/tech needed).
#   sta_run.sh STA_DIR [mount dirs...]
set -uo pipefail
D=$1; shift
IMG=${ORFS_IMAGE:-openroad/orfs:asap7lock}
mounts=(-v "$D:$D"); for m in "$@"; do mounts+=(-v "$m:$m"); done
for v in flat stitched etm; do
  [ -f "$D/$v.tcl" ] || continue
  docker run --rm --memory "${DOCKER_MEM:-16g}" --user "$(id -u):$(id -g)" "${mounts[@]}" "$IMG" \
    /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -no_init -no_splash -exit "$D/$v.tcl" > "$D/$v.log" 2>&1
  echo "$v rc=$? $(grep -c Error "$D/$v.log") errors"
done
