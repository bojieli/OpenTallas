#!/usr/bin/env bash
# TKM-E86 lockstep: ot_hgi_coll_tkm_tile_e86 (row-group roots) vs ot_hgi_coll_tkm_tile EW86/PT64.  run_tile_rg_lockstep.sh OUT [MUT]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd);cd "$ROOT"
OUT=$(realpath -m "${1:?out}");MUT=${2:-0};mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic/collective/tkm
"$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -DSYNTHESIS --top-module tb_hgi_coll_tkm_tile_rg_lockstep \
 -GMUT=$MUT -Mdir "$OUT/obj$MUT" $C/tb_hgi_coll_tkm_tile_rg_lockstep.sv $C/ot_hgi_coll_tkm.sv $C/ot_hgi_coll_tkm_static.sv > "$OUT/build$MUT.log" 2>&1 || { tail -30 "$OUT/build$MUT.log"; exit 2; }
"$OUT/obj$MUT/Vtb_hgi_coll_tkm_tile_rg_lockstep"
