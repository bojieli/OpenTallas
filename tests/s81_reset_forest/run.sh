#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python3 "$root/tests/s81_reset_forest/test_plan.py"
python3 "$root/tests/s81_reset_forest/test_generator_strict.py"
rtl="$root/rtl/dsrom_sys/s81_reset_forest/ot_s81_reset_leaf.sv"
tb="$root/tests/s81_reset_forest/tb_reset_forest.sv"
iverilog -g2012 -s tb_reset_forest -o "$tmp/good" "$rtl" "$tb"
vvp "$tmp/good"
iverilog -g2012 -DMUTANT_EARLY -s tb_reset_forest -o "$tmp/early" "$rtl" "$tb"
if vvp "$tmp/early" >"$tmp/early.log" 2>&1; then
    echo 'ERROR early-release mutant survived'; exit 1
fi
sed 's/posedge ck or negedge upstream_rst_n/posedge ck/' "$rtl" > "$tmp/sync_assert.sv"
iverilog -g2012 -s tb_reset_forest -o "$tmp/sync" "$tmp/sync_assert.sv" "$tb"
if vvp "$tmp/sync" >"$tmp/sync.log" 2>&1; then
    echo 'ERROR synchronous-assertion mutant survived'; exit 1
fi
echo 'PASS early-release and synchronous-assertion mutants rejected'
