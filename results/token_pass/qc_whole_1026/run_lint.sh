#!/bin/bash
set -u
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$HOME/.local/opentallas-tools/bin:$PATH"
verilator --version > version.txt
/usr/bin/time -v -o lint.time verilator --lint-only --timing -Wno-fatal --error-limit 100 --top-module qwen_compute_bound_top -f defines.f -f incdirs.f -f files.f > lint.log 2>&1
qc_lint_rc=$?
printf '%s\n' "$qc_lint_rc" > lint.rc
exit "$qc_lint_rc"
