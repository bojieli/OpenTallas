#!/bin/bash
# ROOT invokes this only through ordinary fleet admission. This file is not a gate.
set -euo pipefail
case_name=${1:?case shell3 or ctlm2}
mode=${2:?mode collector, causals or engine}
work=${3:?fresh absolute output directory}
api_root=${4:?current FRAME API projection root}
here=$(cd "$(dirname "$0")" && pwd)
python3 "$here/prepare_fixture.py" "$case_name" "$work" --api-root "$api_root"
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker image inspect "$image" --format '{{.Id}}' > "$work/tool_image_id.txt"
docker run --rm --network none --memory "${FIXTURE_MEMORY_GB:-32}g" --cpus "${FIXTURE_THREADS:-1}" \
  -w /w -e RESULTS_DIR=/w -e "DSP_FIXTURE_MODE=$mode" -v "$work:/w" -v "$work/src:/src" "$image" \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /w/fixture_modes.tcl \
  > "$work/openroad.log" 2>&1
cat "$work/openroad.log"
