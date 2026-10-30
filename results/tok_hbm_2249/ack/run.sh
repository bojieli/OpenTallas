#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for cfg in '11 11 0 baseline' '11 12 1 delayed_unmatched' '12 12 0 matched';do
 read -r expected actual fault name <<< "$cfg"
 iverilog -g2012 -s tb -Ptb.EXPECT_WR="$expected" -Ptb.ACTUAL_WR="$actual" -Ptb.EXPECT_FAULT="$fault" -o "$name.vvp" bridge.sv tb.sv
 vvp "$name.vvp" > "$name.log"
 cat "$name.log"
done
