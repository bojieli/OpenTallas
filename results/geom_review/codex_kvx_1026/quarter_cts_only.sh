#!/bin/bash
# Reviewed ECTLK quarter checkpoint only; never rebuild prerequisites.
set -eu
K=$(realpath "$1")
test "${2:-cts}" = cts
MEM=${3:-16}
CPUS=${4:-8}
(cd "$K" && sha256sum -c cts_inputs.sha256)
docker run --rm --name "codex-ectlk-cts-$$" --memory="${MEM}g" --cpus="$CPUS" \
  -u "$(id -u):$(id -g)" -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS do-cts"
