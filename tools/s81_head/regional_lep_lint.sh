#!/usr/bin/env bash
set -euo pipefail
mapfile -t lint_sources < tools/s81_head/regional_lep_lint.f
verilator --version
verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DSYNTHESIS -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF --top-module ot_s81hd_lep_regional "${lint_sources[@]}"
echo REGIONAL_HEAD_LINT_PASS
