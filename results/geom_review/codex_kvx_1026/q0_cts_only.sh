#!/bin/bash
# CODEX-ECTLK-Q0-FINAL-1026: one CTS-only trial on the reviewed placement.
set -eu
K=$(realpath "$1")
test "${2:-cts}" = cts
MEM=${3:-16}
CPUS=${4:-8}
R="$K/run/results/asap7/hc_qkd_ectlk_q0__216x172_8/base"
printf '%s  %s\n' \
  6bf8d06e26f13557464404168683b5478703036b7f471932fe447699b5d09f01 "$R/3_place.odb" \
  e7934599566fe46ae8af6d270b3800eab394b5d09d85ccc36ce2f02189653ba7 "$K/pins.json" \
  1dd02ca2034716fab15ea669fc54f75dfbed5bba8a073d5e3f0e8e70c513aa61 "$K/constraint.sdc" | sha256sum -c -
docker run --rm --name "codex-ectlk-q0-cts-$$" --memory="${MEM}g" --cpus="$CPUS" \
  -u "$(id -u):$(id -g)" -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS do-cts"
