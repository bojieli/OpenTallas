#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
P=/srv/opentallas-scratch2/claude/codex-kv-ahub-1026/ahub_seen_bank_1026
for m in 0 1;do
 verilator --binary -j 4 --timing -Wno-fatal -Wno-MULTIDRIVEN --top-module tb -GMUT=$m -Mdir "$P/obj$m" -o Vtb "$P/ref.sv" "$P/dut.sv" "$P/tb.sv" > "$P/build$m.log" 2>&1
 "$P/obj$m/Vtb" > "$P/run$m.log" 2>&1
 cat "$P/run$m.log"
done
