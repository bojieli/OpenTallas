#!/usr/bin/env bash
# TP=192 TKM negative (expect FAIL): the TIE_W_MUT=1 build (192-rank tie id truncated to 7 bits) on rank128_zeros must
# report MISMATCH R / TKM_STATIC FAIL.  Prints the run log; exits with the simulator status.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd);cd "$ROOT"
OUT=$(realpath -m "${1:?out}");mkdir -p "$OUT"
OPENBLAS_NUM_THREADS=1 python3 tools/hgi_coll_tkm_tp192_vectors.py --out "$OUT/vec" > "$OUT/vectors.log" || exit 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic/collective
src=("$C/p2p/qtkm_hier.vlt" "$C/tkm/tb_hgi_coll_tkm_static.sv" "$C/tkm/ot_hgi_coll_tkm_static.sv" "$C/tkm/ot_hgi_coll_tkm.sv" "$C/tkm/ot_hgi_coll_tkm_buffer.sv" rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
"$V" --binary --timing --hierarchical --verilate-jobs 2 --build-jobs 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --top-module tb_hgi_coll_tkm_static -Mdir "$OUT/obj1" -GTP=192 -GKMAX=2048 -GTIE_W_MUT=1 "${src[@]}" > "$OUT/build1.log" 2>&1 || { tail -20 "$OUT/build1.log"; exit 2; }
"$OUT/obj1/Vtb_hgi_coll_tkm_static" +DIR="$OUT/vec/rank128_zeros" +ROTATE=128 > "$OUT/mut.log" 2>&1; rc=$?
grep -E 'MISMATCH R|TKM_STATIC' "$OUT/mut.log" | head -5
exit $rc
