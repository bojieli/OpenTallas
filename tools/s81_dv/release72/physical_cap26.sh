#!/bin/bash
# remote: physical chain of cap26 VARIANT from its staged GEN receipt
set -uo pipefail
V=${1:?variant}
I=/home/ubuntu/ot-scratch/claude/stw-s81c-cap26
R=${OT_SCRATCH:-/srv/opentallas-scratch}/claude/stw-s81c-cap26-$V-physical
mkdir -p "$(dirname "$R")"; mkdir "$R" || exit 2
tar -xzf "$I/cap26_${V}_receipt.tar.gz" -C "$R" || exit 3
printf 'cap26 %s (claude/s81c-cap26-1022) host %s %s\n' "$V" "$(hostname)" "$(date -Is)" > "$R/physical.identity"
echo "$(hostname):$R" > "$I/cap26_${V}_rundir"
CPUS=16 MEMG_GRT=160 MEMG_STA=64 bash "$R/case/run_all.sh" > "$R/chain.log" 2>&1
rc=$?; echo "PHYSICAL_RC $rc $(date -Is)" > "$R/physical.exit"; exit "$rc"
