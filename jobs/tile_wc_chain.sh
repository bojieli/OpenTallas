#!/bin/bash
# usage: jobs/tile_wc_chain.sh <tag> [extra driver args...]   (from the worktree root on the worker)
# WC tile harden (jobs/tile_wc.sh pnr), then SS/FF sign-off STA (jobs/tile_corners.sh) on the kept work dir;
# the small corner logs/reports are copied into the record directory, the heavy work dir stays on the worker.
set -uo pipefail
TAG=$1; shift
KEEP=$HOME/w12bwork/keep_$TAG
OUT=results/physical_hdc/asap7/qwen_o4_w12/tile_$TAG
export OT_FLOW_TIMEOUT_SECONDS=${OT_FLOW_TIMEOUT_SECONDS:-172800}
export OT_PHYSICAL_WORK_ROOT=$HOME/w12bwork/tmp
mkdir -p $OT_PHYSICAL_WORK_ROOT $OUT
bash jobs/tile_wc.sh $TAG pnr --keep-workdir $KEEP "$@" > $OUT/flow.log 2>&1
echo "flow rc=$?" >> $OUT/flow.log
N=opentallas_ot_qwen_rom_tile_asap7_w12_tile_$TAG
if [ -f $KEEP/orfs/results/asap7/$N/base/6_final.odb ]; then
  bash jobs/tile_corners.sh $KEEP $N > $OUT/corners.log 2>&1
  mkdir -p $OUT/corners
  cp $KEEP/corner_ss.log $KEEP/corner_ff.log $KEEP/orfs/corner_*_max.rpt $KEEP/orfs/corner_*_min.rpt $KEEP/orfs/corner_ss_ends.rpt $KEEP/orfs/corner_ss_in2reg*.rpt $KEEP/orfs/corner_ss_reg2out.rpt $OUT/corners/ 2>/dev/null
  for r in 6_finish.rpt 6_report.json; do cp $KEEP/orfs/reports/asap7/$N/base/$r $OUT/corners/ 2>/dev/null; done
  cp $KEEP/orfs/logs/asap7/$N/base/6_report.json $OUT/corners/ 2>/dev/null
fi
