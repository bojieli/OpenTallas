#!/usr/bin/env bash
# HBM-TAPS 11-12 ISS2E end-to-end ARG bench on the REAL q3bc parent ot_hfd_coll_q3_hard_v8x_s (NLINK 3, TP 192, VM_RT 81,
# ROWS 256, ARG argmax_m_tp192_pr) through run_coll_v8x_argmax.sh (tb copy with the _s parent).  DO_NOT_COUNT.
#   run_coll_v8x_s_argmax_iss2e.sh OUT MODE
# MODE iss2e     : -DOT_COLL_ISSUER256_ISS2E + BANK_RQREG + the compiler's union pad / hold masks (row_gather_rows.py
#                  --issue-cadence 2 --arg-start-reg --arg-pr-source manifest), argmax_rows --issue-cadence 2
#                  --start-reg --arg-pr-source, P1 P6 P8 -> PASS
#      notaprep  : same with OT_COLL_ISS8E_MUT_NOTAPREP (no tap repeat in the pad window) -> FAIL (P6/P8 addr)
#      nopad     : ISS2E, C=2 programme, no masks -> FAIL
#      ref       : v7 issuer (no ISS2E), C=1 programme, P6 -> PASS
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd); ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); MODE=${2:?mode}; mkdir -p "$OUT"; cd "$ROOT"
p=rtl/hbm_accel/generic/collective/p2p
sed 's/ ot_hfd_coll_q3_hard_v8x #(/ ot_hfd_coll_q3_hard_v8x_s #(/' "$p/tb_hgi_coll_v8x_argmax.sv" > "$OUT/tb_v8x_s_argmax.sv"
grep -q 'ot_hfd_coll_q3_hard_v8x_s #(' "$OUT/tb_v8x_s_argmax.sv"
python3 tools/hbm_coll_static/row_gather_rows.py "$OUT/rg_mask" --P 1 --vm-rt 81 --issue-cadence 2 --arg-start-reg --arg-pr-source > "$OUT/rg_mask.log"
read -r PM HM < <(python3 - "$OUT/rg_mask/manifest.json" <<'PY'
import json, sys
def find(d, k):
    if isinstance(d, dict):
        for kk, vv in d.items():
            if kk == k: return vv
            r = find(vv, k)
            if r is not None: return r
m = json.load(open(sys.argv[1])); print(find(m, "issue_pad_mask"), find(m, "issue_hold_mask"))
PY
)
echo "pad $PM" > "$OUT/masks.txt"; echo "hold $HM" >> "$OUT/masks.txt"
export NLINK=3 TP=192 ARG_VMRT=81 ARG_TB="$OUT/tb_v8x_s_argmax.sv" ARG_CASES="1 6 8"
SS="$p/ot_hfd_coll_q3_hard_v8x_s.sv $p/ot_hgi_coll_edge_pr.sv $p/ot_hfd_coll_q2_hard_v8g_s.sv $p/ot_hgi_coll_reduce_static_pr.sv"
E="$p/ot_hgi_coll_issuer_m256v8e.sv"
B="+define+OT_COLL_ISSUER256_ISS2E +define+OT_COLL_ISS8E_BANK_RQREG"
case $MODE in
 iss2e)    export ARG_VSRC="$E $SS" ARG_VDEFS="$B +define+OT_COLL_ISS8E_PAD_MASK=$PM +define+OT_COLL_ISS8E_HOLD_MASK=$HM" ARG_CARGS="--issue-cadence 2 --arg-pr-source";;
 notaprep) export ARG_VSRC="$E $SS" ARG_VDEFS="$B +define+OT_COLL_ISS8E_PAD_MASK=$PM +define+OT_COLL_ISS8E_HOLD_MASK=$HM +define+OT_COLL_ISS8E_MUT_NOTAPREP" ARG_CARGS="--issue-cadence 2 --arg-pr-source";;
 nopad)    export ARG_VSRC="$E $SS" ARG_VDEFS="$B" ARG_CARGS="--issue-cadence 2 --arg-pr-source";;
 ref)      export ARG_VSRC="$SS" ARG_CARGS="--arg-pr-source" ARG_CASES=6;;
 *) echo "unknown mode $MODE"; exit 2;;
esac
set +e; bash "$p/run_coll_v8x_argmax.sh" "$OUT/run" pass > "$OUT/$MODE.log" 2>&1; rc=$?; set -e
grep -E '^ARGMAX_ROWS (PASS|FAIL)|GATE' "$OUT/$MODE.log" || true
case $MODE in iss2e|ref) [ $rc = 0 ] && echo "ISS2E_ARG_S $MODE PASS"; exit $rc;;
 *) if [ $rc != 0 ]; then echo "ISS2E_ARG_S_MUTANT_REJECTED $MODE"; exit 0; fi; echo "ISS2E_ARG_S_MUTANT_SURVIVED $MODE"; exit 1;; esac
