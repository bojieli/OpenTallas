#!/bin/bash
set -euo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
MODE=${2:-pass};MUT=0
[[ $MODE == mut ]] && MUT=1
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
sha256sum rtl/physical/qcluster/qfd_c_reset_group16_safe.sv rtl/test/tb_qfd_c_reset_group16_safe.sv "$0" > "$OUT/sources.sha256"
"$V" --binary --timing -j 4 -O1 -Wno-fatal --top-module tb -GMUT=$MUT -Mdir "$OUT/obj" rtl/physical/qcluster/qfd_c_reset_group16_safe.sv rtl/test/tb_qfd_c_reset_group16_safe.sv > "$OUT/build.log" 2>&1
exec "$OUT/obj/Vtb"
