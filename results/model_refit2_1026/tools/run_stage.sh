#!/bin/bash
# usage: run_stage.sh KITDIR RESULTS_REL OUTDIR  (TT+FF stage dump + sink TSV on the GRT ODB, read-only kit mount)
K=$1; B=$2; O=$3; T=/srv/opentallas-scratch2/claude/model-refit2-1026/tools
mkdir -p $O
for C in TT FF; do
 for M in meas_stage meas_ck; do
  timeout 900 docker run --rm --memory=12g --memory-swap=12g --cpus=2 -v $K:/work:ro -v $O:/out -v $T/$M.tcl:/m.tcl:ro \
   -e ODB=/work/$B/5_1_grt.odb -e SDC=/work/$B/5_1_grt.sdc -e OT_CORNER=$C -e OUT=/out/${M}_$C.tsv openroad/orfs:asap7lock \
   bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /m.tcl" > $O/${M}_$C.log 2>&1 &
 done
done
wait; docker run --rm -v $O:/out openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /out
grep -h -c "STAGE_DONE\|MEAS_DONE" $O/*.log
