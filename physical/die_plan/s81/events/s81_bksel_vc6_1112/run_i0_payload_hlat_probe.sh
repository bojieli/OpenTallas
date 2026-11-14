#!/bin/bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
OUT=$1
mkdir -p "$OUT"
iverilog -g2012 -s tb -o "$OUT/exact" "$HERE/i0_payload_hlat_probe.sv"
vvp "$OUT/exact" | tee "$OUT/exact.log"
iverilog -g2012 -s tb -DI0_OUT_STALE_MUT -o "$OUT/mutant" "$HERE/i0_payload_hlat_probe.sv"
vvp "$OUT/mutant" | tee "$OUT/mutant.log"
