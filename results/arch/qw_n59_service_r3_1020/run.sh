#!/bin/bash
set -uo pipefail
unit=$1
root=/srv/opentallas-scratch/claude/codex-qw-n59-service-r3-1020
run=$root/$unit
mkdir -p "$run/src"
tar -xzf "$root/source.tgz" -C "$run/src"
tar -xzf "$root/overlay.tgz" -C "$run/src"
cd "$run/src"
bash results/arch/qw_n59v6_service_1020/bench.sh "$unit" "$run/out" > "$run/bench.log" 2>&1
rc=$?
printf 'N59_V6_DONE case=%s rc=%s\n' "$unit" "$rc" | tee "$run/DONE"
exit "$rc"
