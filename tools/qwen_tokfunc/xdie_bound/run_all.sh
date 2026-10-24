#!/bin/bash
# TOK-QW xdie_bound: everything, from the repository root of a checkout (or git archive) of the revision under test.
#   run_all.sh OUTDIR  -> OUTDIR/{carve/ (literal bound carves + elaboration), regen/ (regenerated pair image),
#                          audit.json, cosim/ (run_xdie_bound.sh configs)}; RESULT line at the end.
set -u
O=$(realpath -m "$1"); mkdir -p "$O"
X=tools/qwen_tokfunc/xdie_bound
echo "rev $(cat REVISION 2>/dev/null || git rev-parse HEAD) host $(hostname) start $(date -Is)" | tee "$O/RUN.txt"
$X/carve_elab.sh "$O/carve" > "$O/carve.log" 2>&1; echo "carve_elab rc=$?" >> "$O/RUN.txt"
D2D_DIE_STAGES=2,2,2,3,2,2/34,34,32,32,32,31,31 D2D_MU=1 D2D_EMB_WINDOW=595 D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213 \
  bash tools/qwen_split/d2d_cal_image_production.sh "$O/regen" > "$O/regen.log" 2>&1; echo "regen rc=$?" >> "$O/RUN.txt"
python3 $X/bound_xdie_audit.py --regen "$O/regen/d2d_cal_image.svh" --out "$O/audit.json" \
  --closure "$O/carve/qc_closure.json" --closure "$O/carve/kv_closure.json" > "$O/audit.txt" 2>&1; echo "audit rc=$?" >> "$O/RUN.txt"
JOBS=${JOBS:-2} $X/run_xdie_bound.sh "$O/cosim" > "$O/cosim.log" 2>&1; rc=$?; echo "cosim rc=$rc" >> "$O/RUN.txt"
echo "end $(date -Is)" >> "$O/RUN.txt"
cat "$O/carve/ELAB.txt" "$O/audit.txt" "$O/cosim/SUMMARY.txt" 2>/dev/null | grep -E '^(qc|kv|F|K)|expect='
echo "RESULT cosim_all_expected=$([ $rc = 0 ] && echo YES || echo NO)"
