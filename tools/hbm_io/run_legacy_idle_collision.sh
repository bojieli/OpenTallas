#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mkdir -p "$out"
iverilog -g2012 -s tb_legacy_idle_collision -o "$out/gate.vvp" "$root/rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv" "$root/rtl/hbm_accel/io_static_20261015/tb_legacy_idle_collision.sv"
vvp "$out/gate.vvp" > "$out/counterexample.log" 2>&1
cat "$out/counterexample.log"
grep -q COUNTEREXAMPLE_CONFIRMED "$out/counterexample.log"
