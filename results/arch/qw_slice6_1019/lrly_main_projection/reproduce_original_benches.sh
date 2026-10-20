#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "${1:?output directory required}")
cd "$(dirname "$0")/source_snapshot"
bash rtl/test/qwen_dv/s5/run_s5.sh "$OUT/positive" eq 0
bash rtl/test/qwen_dv/s5/run_s5.sh "$OUT/mutant" eq lrly
