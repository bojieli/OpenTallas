#!/bin/bash
set -euo pipefail
case_dir=/srv/opentallas-scratch/claude/ref_gate/dsdv_mu_hwin_c21h-20261019-213545/routes/gate/work/orfs
out=/srv/opentallas-scratch/claude/codex-hwin-native-1020/c21h_native_endpoint
mkdir -p "$out"
docker run --rm -v "$case_dir:/work:ro" -v "$out:/out" -v "$PWD/native_endpoint_extract.py:/extract.py:ro" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 && openroad -exit -python /extract.py'
