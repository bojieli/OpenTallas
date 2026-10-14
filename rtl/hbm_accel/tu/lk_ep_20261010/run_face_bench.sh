#!/bin/bash
set -euo pipefail
out=$1; mut=${2:-0};mkdir -p "$out"
VER=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
base=rtl/hbm_accel/tu/lk_ep_20261010
"$VER" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_lkep_face -GMUT_FACE="$mut" --Mdir "$out/obj" -o sim "$base/hfd_lk_ep.sv" "$base/hfd_lk_ep_face.sv" "$base/hfd_lk_ep_face_golden.sv" "$base/tb_lkep_face.sv" > "$out/build.log" 2>&1
set +e
"$out/obj/sim" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
exit "$rc"
