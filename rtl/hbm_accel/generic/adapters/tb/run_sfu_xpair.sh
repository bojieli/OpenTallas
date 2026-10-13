#!/usr/bin/env bash
set -euo pipefail
sfupair_root=$(cd "$(dirname "$0")/../../../../.." && pwd)
sfupair_out=$(realpath "$1"); mode=${2:-lint}; mut=${3:-0}; fmt=${4:-0}
cd "$sfupair_root"
mapfile -t sfupair_files < rtl/hbm_accel/generic/adapters/tb/sfu_xpair_files.txt
sfupair_vl="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
if [ "$mode" = lint ]; then
    "$sfupair_vl" --lint-only --timing -Wno-fatal --top-module tb_hgi_sfu_xpair -I"$sfupair_out/vec" "${sfupair_files[@]}"
else
    "$sfupair_vl" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
        --top-module tb_hgi_sfu_xpair -I"$sfupair_out/vec" -DMUT_WM="$mut" -DXFMT="$fmt" \
        -Mdir "$sfupair_out/obj_m${mut}_f${fmt}" "${sfupair_files[@]}" -j "${JOBS:-16}" \
        > "$sfupair_out/build_m${mut}_f${fmt}.log" 2>&1
    "$sfupair_out/obj_m${mut}_f${fmt}/Vtb_hgi_sfu_xpair" +DIR="$sfupair_out/vec" \
        > "$sfupair_out/run_m${mut}_f${fmt}.log" 2>&1
fi
