#!/bin/bash
# one constructor variant in its own source copy (lane root): bash variant.sh LANEROOT NAME  (XH_FLAGS = constructor flags)
set -uo pipefail
R=$1; N=$2; V=$R/$N; rm -rf "$V"; mkdir -p "$V"; cp -a "$R/src" "$V/src"; cd "$V/src"
bash rtl/test/qwen_dv/s5/xhead7/chain.sh "$V/out" > "$V/chain.log" 2>&1; cat "$V/chain.log" | grep -v '^ *"' | tail -20
