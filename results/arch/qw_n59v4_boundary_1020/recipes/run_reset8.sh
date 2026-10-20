#!/bin/bash
set -uo pipefail
root=/srv/opentallas-scratch/claude/codex-qw-n59v4-align-1020
run=$root/reset8
mkdir -p "$run/src"
tar -xzf "$root/source.tgz" -C "$run/src"
tar -xzf "$root/reset8.tgz" -C "$run/src"
cd "$run/src"
export N59_QB_ALIGN=1
bash results/arch/qw_n59v4_boundary_1020/bench.sh recv_reset8 "$run/out" > "$run/bench.log" 2>&1
rc=$?
printf 'N59_RESET8_DONE rc=%s\n' "$rc" | tee "$run/DONE"
exit "$rc"
