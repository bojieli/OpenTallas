#!/usr/bin/env bash
# PL-TP192 10-18: golden bench (tb_hgi_coll_tkm_static vectors at TP 192 / KMAX 2048) on the TKM TP192 sub-cluster:
#   flat reference ot_hgi_coll_tkm_m_tp192_seg MUT 0: syn_sel, syn_cand, rank128_zeros PASS
#   flat CTL_MUT 3 (segment conv strobes not compensated for the up seams): syn_sel FAIL (MISMATCH O)
#   landed ot_hgi_coll_tkm_m_tp192_lp (lp.py output, all region clocks = clk) MUT 0: syn_sel PASS
# Fleet only (ot-run), Verilator 5.050 --hierarchical (qtkm_hier.vlt: the e86 tile is compiled once).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd);cd "$ROOT"
OUT=$(realpath -m "${1:?out}");mkdir -p "$OUT"
OPENBLAS_NUM_THREADS=1 python3 tools/hgi_coll_tkm_tp192_vectors.py --out "$OUT/vec" > "$OUT/vectors.log"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic/collective
common=("$C/p2p/qtkm_hier.vlt" "$C/tkm/tb_hgi_coll_tkm_m_tp192_seg.sv" "$C/tkm/ot_hgi_coll_tkm_ctl.sv" "$C/tkm/ot_hgi_coll_tkm_static.sv" "$C/tkm/ot_hgi_coll_tkm.sv" "$C/tkm/ot_hgi_coll_tkm_buffer.sv" rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/common/landed_parent/ot_pl_land.sv)
flat=("$C/tkm/ot_hgi_coll_tkm_m_tp192_seg.sv")
lp=("$C/tkm/lp/ot_hgi_coll_tkm_m_tp192_lp.sv")
sha256sum "${common[@]}" "${flat[@]}" "${lp[@]}" tools/hgi_coll_tkm_tp192_vectors.py tools/hgi_coll_tkm_vectors.py > "$OUT/sources.sha256"
build(){ # tag mut define files...
 local tag=$1 mut=$2 def=$3;shift 3
 "$V" --binary --timing --hierarchical --verilate-jobs 4 --build-jobs 16 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT \
  --top-module tb_hgi_coll_tkm_m_tp192_seg -Mdir "$OUT/obj_$tag" -GTP=192 -GKMAX=2048 -GMUT=$mut $def "${common[@]}" "$@" > "$OUT/build_$tag.log" 2>&1
}
rc=0
build flat0 0 "" "${flat[@]}"
for tc in syn_sel syn_cand rank128_zeros;do
 "$OUT/obj_flat0/Vtb_hgi_coll_tkm_m_tp192_seg" +DIR="$OUT/vec/$tc" +ROTATE=128 > "$OUT/flat0_$tc.log" 2>&1 || true
 if grep -q 'TKM_STATIC PASS' "$OUT/flat0_$tc.log";then echo "FLAT MUT0 $tc PASS";else echo "FLAT MUT0 $tc FAIL";rc=1;fi
done
build flat3 3 "" "${flat[@]}"
set +e;"$OUT/obj_flat3/Vtb_hgi_coll_tkm_m_tp192_seg" +DIR="$OUT/vec/syn_sel" +ROTATE=128 > "$OUT/flat3_syn_sel.log" 2>&1;r3=$?;set -e
if [ "$r3" != 0 ] && grep -q 'MISMATCH O' "$OUT/flat3_syn_sel.log" && grep -q 'TKM_STATIC FAIL' "$OUT/flat3_syn_sel.log";then echo "FLAT CTL_MUT3 syn_sel FAIL (expected)";else echo "FLAT CTL_MUT3 syn_sel did not FAIL";rc=1;fi
build lp0 0 "+define+TKM_LP" "${lp[@]}"
"$OUT/obj_lp0/Vtb_hgi_coll_tkm_m_tp192_seg" +DIR="$OUT/vec/syn_sel" +ROTATE=128 > "$OUT/lp0_syn_sel.log" 2>&1 || true
if grep -q 'TKM_STATIC PASS' "$OUT/lp0_syn_sel.log";then echo "LANDED MUT0 syn_sel PASS";else echo "LANDED MUT0 syn_sel FAIL";rc=1;fi
[ $rc = 0 ] && echo TKM_TP192_SEG_GATE_PASS || echo TKM_TP192_SEG_GATE_FAIL
exit $rc
