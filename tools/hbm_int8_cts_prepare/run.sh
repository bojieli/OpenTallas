#!/bin/bash
# Run ONLY on an admitted unpinned ot-run fleet snapshot after explicit ROOT grant.
set -euo pipefail
: "${INT8_CTS_WORK:?isolated snapshot path required}"
: "${INT8_CTS_ROOT_APPROVAL:?exact ROOT approval JSON required}"
python3 "$INT8_CTS_WORK/kit/validate_inputs.py" "$INT8_CTS_WORK" "$INT8_CTS_ROOT_APPROVAL"
mkdir -p "$INT8_CTS_WORK/output"
test ! -e "$INT8_CTS_WORK/output/cts_only.odb"
docker run --rm --user "$(id -u):$(id -g)" -v "$INT8_CTS_WORK:/work" sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/kit/cts_only.tcl > "$INT8_CTS_WORK/output/cts.log" 2>&1
