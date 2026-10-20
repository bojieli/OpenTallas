#!/bin/bash
set -uo pipefail
root=/srv/opentallas-scratch/claude/qw-n59-5-qage; run=$root/$1; rm -rf "$run"; mkdir -p "$run/src"
tar -xzf "$root/source.tgz" -C "$run/src"; cd "$run/src"
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
bash rtl/test/qwen_split/run_n59_qage.sh "$run/out" > "$run/bench.log" 2>&1; rc=$?
tail -n 3 "$run/bench.log"; printf 'N59QAGE_DONE rc=%s\n' "$rc" | tee "$run/DONE"; exit $rc
