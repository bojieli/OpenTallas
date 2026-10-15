#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
iverilog -g2012 -s tb -o "$build/exact" qkd_result_static.sv tb.sv
vvp "$build/exact"
iverilog -g2012 -s tb -Ptb.MUT=1 -o "$build/mutant" qkd_result_static.sv tb.sv
if vvp "$build/mutant" >"$build/mutant.log" 2>&1; then
 cat "$build/mutant.log"
 echo 'FAIL data mutant survived'; exit 1
fi
if ! grep -q 'record mismatch context=0 beat=17' "$build/mutant.log"; then
 cat "$build/mutant.log"; exit 1
fi
cat "$build/mutant.log"
echo 'PASS data mutant rejected at exact producer-local beat17'
sha256sum qkd_result_static.sv tb.sv
