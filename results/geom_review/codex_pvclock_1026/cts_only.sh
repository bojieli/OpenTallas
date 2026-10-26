#!/bin/bash
set -eu
K=$(realpath "$1")
test "${2:-cts}" = cts
MEM=${3:-16}
CPUS=${4:-8}
R="$K/run/results/asap7/hc_kv3_pv_pair__380_16x190_08/base"
printf '%s  %s\n' 26582c7d3e4ab532beb05ad7f53f931465f4d0ab9776ffc4b2d72b3bcb623a15 "$R/3_place.odb" | sha256sum -c -
docker run --rm --name "codex-pvclock-cts-$$" --memory="${MEM}g" --cpus="$CPUS" \
  -u "$(id -u):$(id -g)" -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS do-cts"
