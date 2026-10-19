#!/bin/bash
set -e
for mode in spine tap; do
  docker run --rm --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -v "$PWD/fixture":/fixture -v "$PWD/source":/source:ro -e OT_PG_CANARY_ROOT=/fixture -e OT_PG_CANARY_SOURCE=/source -e OT_PG_CANARY_DB=/fixture/3_place.odb -e OT_PG_STRICT=1 -e SCRIPTS_DIR=/fixture -e OT_PG_CANARY_MODE=$mode -e OT_PG_CANARY_PAD=1 -e OT_PG_CANARY_DIRTY=1 sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 -exit /fixture/cts.tcl > targeted_${mode}.log 2>&1
  tail -6 targeted_${mode}.log
done
