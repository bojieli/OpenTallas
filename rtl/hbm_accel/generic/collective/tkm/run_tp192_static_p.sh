#!/usr/bin/env bash
# HBM-P4-SPLIT: TP192 TKM core-split twin gate. PIPE 1 golden vectors (3 cases) + lock-step vs the pinned root (+2 edges);
# PIPE 0 identity (one case); mutant MUTP 1 (up[0] consumed one edge early) must FAIL.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd);cd "$ROOT"
OUT=$(realpath -m "${1:?out}");mkdir -p "$OUT"
[ -d "$OUT/vec" ] || OPENBLAS_NUM_THREADS=1 python3 tools/hgi_coll_tkm_tp192_vectors.py --out "$OUT/vec" > "$OUT/vectors.log"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic/collective
src=("$C/p2p/qtkm_hier.vlt" "$C/tkm/tb_hgi_coll_tkm_static_p.sv" "$C/tkm/ot_hgi_coll_tkm_static_p.sv" "$C/tkm/ot_hgi_coll_tkm_static.sv" "$C/tkm/ot_hgi_coll_tkm.sv" "$C/tkm/ot_hgi_coll_tkm_buffer.sv" rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
sha256sum "${src[@]}" tools/hgi_coll_tkm_tp192_vectors.py tools/hgi_coll_tkm_vectors.py > "$OUT/sources.sha256"
build(){ "$V" --binary --timing --hierarchical --verilate-jobs 2 --build-jobs ${JOBS:-8} -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --top-module tb_hgi_coll_tkm_static_p -Mdir "$OUT/obj_$1" -GTP=192 -GKMAX=2048 -GPIPE=$2 -GMUTP=$3 "${src[@]}" > "$OUT/build_$1.log" 2>&1; }
build p1 1 0; build p0 0 0; build mut 1 1
for tc in syn_sel syn_cand rank128_zeros;do
 "$OUT/obj_p1/Vtb_hgi_coll_tkm_static_p" +DIR="$OUT/vec/$tc" +ROTATE=128 > "$OUT/p1_$tc.log" 2>&1
 grep 'TKM_STATIC_P PASS' "$OUT/p1_$tc.log"
done
"$OUT/obj_p0/Vtb_hgi_coll_tkm_static_p" +DIR="$OUT/vec/syn_sel" +ROTATE=128 > "$OUT/p0_syn_sel.log" 2>&1
grep 'TKM_STATIC_P PASS' "$OUT/p0_syn_sel.log"
set +e
"$OUT/obj_mut/Vtb_hgi_coll_tkm_static_p" +DIR="$OUT/vec/syn_sel" +ROTATE=128 > "$OUT/mut_syn_sel.log" 2>&1
rc=$?
set -e
[ "$rc" != 0 ] && grep -q 'TKM_STATIC_P FAIL' "$OUT/mut_syn_sel.log" && echo "MUTANT MUTP1 FAILS as required: $(grep -m1 'TKM_STATIC_P FAIL' "$OUT/mut_syn_sel.log")"
echo TKM_TP192_STATIC_P_GATE_PASS
