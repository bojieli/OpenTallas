#!/bin/bash
# remote: physical chain of cap28 VARIANT from its staged GEN receipt (STW-S81c-DIE3-C28)
set -uo pipefail
V=${1:?variant}
I=/home/ubuntu/ot-scratch/claude/stw-s81c-cap28
R=${OT_SCRATCH:-/srv/opentallas-scratch}/claude/stw-s81c-cap28-$V-physical
mkdir -p "$(dirname "$R")"; mkdir "$R" || exit 2
tar -xzf "$I/cap28_${V}_receipt.tar.gz" -C "$R" || exit 3
printf 'cap28 %s (claude/s81c-cap28-1022) host %s %s DIECLK_ITERS=%s\n' "$V" "$(hostname)" "$(date -Is)" "${DIECLK_ITERS:-6}" > "$R/physical.identity"
echo "$(hostname):$R" > "$I/cap28_${V}_rundir"
DIECLK_ITERS=${DIECLK_ITERS:-6} CPUS=16 MEMG_GRT=160 MEMG_STA=64 bash "$R/case/run_all.sh" > "$R/chain.log" 2>&1
rc=$?; echo "PHYSICAL_RC $rc $(date -Is)" > "$R/physical.exit"; exit "$rc"
