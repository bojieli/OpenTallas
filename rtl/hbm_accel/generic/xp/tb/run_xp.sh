#!/usr/bin/env bash
# usage: run_xp.sh <vec.mem> <nrec> <outdir> [MUT_DROP|MUT_RET|MUT_XRS] [+JIT=n]
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); VEC=$1; N=$2; O=$3; M=${4:-}; shift 4 || shift $#
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$O"
"$VL" --binary --timing -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -GNREC=$N ${M:+-G$M=1} --top-module tb_hgi_xp \
  -Mdir "$O/obj" "$H/../ot_hgi_xp.sv" "$H/tb_hgi_xp.sv" > "$O/build.log" 2>&1 || { grep -E '%Error' -A3 "$O/build.log" | head -40; exit 2; }
"$O/obj/Vtb_hgi_xp" +VEC="$VEC" "$@" | tee "$O/run.log" | tail -${TAIL:-12}
