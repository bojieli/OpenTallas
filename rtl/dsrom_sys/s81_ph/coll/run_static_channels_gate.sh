#!/usr/bin/env bash
set -euo pipefail
base=$(cd -- "$(dirname -- "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
verilator --lint-only -Wall --top-module dsfd_coll_static_channels "$base/dsfd_coll_static_channels.sv"
iverilog -g2012 -s tb_static_channels -o "$work/good" "$base/dsfd_coll_static_channels.sv" "$base/test/tb_static_channels.sv"
vvp "$work/good"
iverilog -g2012 -s tb_static_channels -Ptb_static_channels.MUT=1 -o "$work/bad" "$base/dsfd_coll_static_channels.sv" "$base/test/tb_static_channels.sv"
if vvp "$work/bad" > "$work/mutant.log" 2>&1; then
  echo 'FAIL: actual payload mutant survived'; exit 1
fi
if ! grep -q 'tx payload/calendar lane0 kind0' "$work/mutant.log"; then
  cat "$work/mutant.log"; exit 1
fi
cat "$work/mutant.log"
echo 'PASS: actual DUT payload mutant rejected'
sha256sum "$base/dsfd_coll_static_channels.sv" "$base/test/tb_static_channels.sv"
