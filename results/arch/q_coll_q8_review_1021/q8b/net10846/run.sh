#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum inputs/checkpoint.odb inputs/*.lef inputs/*.sv dump.tcl > before.sha256
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker image inspect "$image" --format '{{.Id}}' > tool_image_id.txt
docker run --rm --network none --memory 7g --cpus 1 -e "DUMP_NET=${DUMP_NET:?actual failed net}" \
  -v "$PWD/inputs:/inputs:ro" -v "$PWD:/w" -w /w "$image" \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /w/dump.tcl > dump.log 2>&1
sha256sum inputs/checkpoint.odb inputs/*.lef inputs/*.sv dump.tcl > after.sha256
cmp before.sha256 after.sha256
tail -n 1 dump.log
