#!/bin/bash
# qwen-missing 2026-10-07: embedding parent PDN-0233 fix, RE-HARDEN variant, as one closure-loop route stage.
#   1. route the ingress child with the M4-pin PDN on M2-M4 (cfg qfd_embed_ingress_<kind>_m4pin)
#   2. export its SS/TT/FF view + measured internal clock reference into the source snapshot (m4c/<kind>)
#   3. route the parent against that view (cfg qfd_embed_<kind>_bank_parent_m4c)
# usage: SRC=<snapshot> reharden.sh KIND LABEL OUTROOT       (the parent route is OUTROOT/LABEL, the child OUTROOT/LABEL_child)
set -uo pipefail
KIND=$1; LABEL=$2; OUT=$3; SRC=${SRC:?}
cd $SRC
export OT_MM_FF_SDC_PARENT=${OT_MM_FF_SDC:-}
OT_MM_FF_SDC=physical/qwen_die_masters/signoff/qfd_embed_ingress_${KIND}_m4pin.sdc SRC=$SRC \
  bash physical/qwen_die_masters/jobs/route_master.sh qfd_embed_ingress_${KIND}_m4pin ${LABEL}_child $OUT || { echo "child route failed" >&2; exit 2; }
python3 tools/qwen_missing/export_ingress_view.py --orfs-dir $OUT/${LABEL}_child/work/orfs --kind $KIND \
  --out physical/qwen_embedding_parent/m4c/$KIND > $OUT/${LABEL}_child/export.log 2>&1 || { echo "child export failed" >&2; exit 3; }
mkdir -p $OUT/$LABEL && cp -r physical/qwen_embedding_parent/m4c/$KIND $OUT/$LABEL/child_view
OT_MM_FF_SDC=${OT_MM_FF_SDC_PARENT:-physical/qwen_die_masters/signoff/qfd_embed_${KIND}_bank_parent_m4c.sdc} SRC=$SRC \
  bash physical/qwen_die_masters/jobs/route_master.sh qfd_embed_${KIND}_bank_parent_m4c $LABEL $OUT
