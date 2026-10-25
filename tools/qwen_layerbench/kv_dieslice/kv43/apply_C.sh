#!/bin/bash
# TOK-QK/C 2026-10-24: apply KV boot fixes C1 + C2 (design fixes: PHY halves on clk_phy behind ONE async-FIFO crossing each,
# order-based half join, core-clock host adapter with paced transmit slots) to a COPY of a staged kv42/kv43 vehicle tree.
#   apply_C.sh STAGED_TREE [BO1_HUBWI]
# STAGED_TREE = stage_src.sh layout (files.f incdirs.f hostside.f src/); edited in place (run it on a copy).  Idempotent.
# BO1_HUBWI default = epyc2 /srv/opentallas-scratch2/claude/codex-qwen/boot_bo1_bound_candidate/kv3_hub_Wi_part.sv.
# Prints every file it changes.  build.sh (strip_default_params.py) is unaffected: no partition gains header parameters.
set -eu
H=$(cd "$(dirname "$0")" && pwd); R=$(cd $H/../../../.. && pwd)
V=${1:?usage: apply_C.sh STAGED_TREE [BO1_HUBWI]}
B=${2:-/srv/opentallas-scratch2/claude/codex-qwen/boot_bo1_bound_candidate/kv3_hub_Wi_part.sv}
[ -f $V/files.f ] && [ -d $V/src/bind__rtl ] || { echo "apply_C: $V is not a staged vehicle tree"; exit 2; }
python3 $H/apply_C.py $V $B $R
