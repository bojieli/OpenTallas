#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=${1:?output directory};mkdir -p "$OUT"
p=$ROOT/rtl/hbm_accel/generic/collective/p2p
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for mode in positive data wrap;do
 params=();[[ $mode != data ]] || params+=(-GMUT_DATA=1);[[ $mode != wrap ]] || params+=(-GMUT_WRAP=1)
 "$V" --binary --timing -O2 -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_hgi_coll_bridge_program_network --Mdir "$OUT/$mode/obj" "${params[@]}" \
 "$p/tb_hgi_coll_bridge_program_network.sv" "$p/ot_hgi_coll_bridge_program.sv" "$p/ot_hgi_coll_quarter_bridge_programmed.sv" \
 "$p/ot_hgi_coll_quarter_bridge.sv" "$p/ot_hgi_coll_static_issuer.sv" \
 "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" > "$OUT/$mode.build.log" 2>&1 || { tail -30 "$OUT/$mode.build.log";exit 2; }
 set +e
 "$OUT/$mode/obj/Vtb_hgi_coll_bridge_program_network" > "$OUT/$mode.log" 2>&1
 rc=$?
 set -e
 cat "$OUT/$mode.log"
 if [[ $mode == positive ]];then [[ $rc == 0 ]];grep -q '^BRIDGE_PROGRAM_NETWORK PASS ' "$OUT/$mode.log"
 else [[ $rc != 0 ]];grep -Eq 'programmednetwork fault|networkvalid mismatch|payload mismatch' "$OUT/$mode.log";echo "NETWORK MUTANT PASS $mode intended_rejection=$rc";fi
done
