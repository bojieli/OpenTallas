#!/bin/bash
set -euo pipefail
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
for case_name in missing omit_post context; do
 mkdir -p "output/$case_name"
 script=cts.tcl
 if [ "$case_name" = missing ]; then script=negative.tcl; fi
 docker run --rm --network none -v "$PWD:/src" -w /src -e CASE="$case_name" "$IMG" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/src/tests/pg_standard_flow_1019/$script" >"output/$case_name/native.log" 2>&1
done
