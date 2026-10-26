#!/bin/bash
set -eu
B=/srv/opentallas-scratch2/claude/codex-genphys-ab-2144
for PHASE in tt ff; do
 if [ "$PHASE" = ff ]; then
 python3 - "$B" <<'PY'
from pathlib import Path
import shutil,sys
p=Path(sys.argv[1]); a=p/'seq_tt';k=p/'seq_ff';shutil.copytree(a,k)
r=k/'run/results/asap7/dp_hd_turn_a/base'
for n,src in [('4_cts.odb','5_1_grt.odb'),('4_cts.sdc','5_1_grt.sdc')]:
 (r/n).unlink();shutil.copy2(r/src,r/n)
for sub in ['results','logs','reports']:
 for f in list((k/'run'/sub).glob('asap7/*/base/5*')):
  d=k/'tt_stage_artifacts'/sub;d.mkdir(parents=True,exist_ok=True);f.rename(d/f.name)
PY
 fi
 K=$B/seq_$PHASE
 docker run --rm --name genphys-seq-$PHASE-2144 --cpus 8 --memory 24g --memory-swap 24g -v "$K":/work -e AB_PHASE="$PHASE" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"
 if [ "$AB_PHASE" = tt ]; then C=TC; c=tc; else C=BC; c=bc; fi
 OT_VCLK_CORNER=$AB_PHASE $M grt CORNER=$C CORNERS=$c HOLD_SLACK_MARGIN=5 > /work/seq_grt.log 2>&1
 rc=$?; echo "$rc" > /work/seq_grt.rc
 if [ "$rc" = 0 ]; then
  O5=$(find /work/run/results -name 5_1_grt.odb | head -1)
  for c in TT FF; do
   OT_POSTCTS_GRT=1 OT_CORNER=$c ODB=$O5 openroad -exit /work/postcts_gate.tcl > /work/seq_sta_$c.log 2>&1
   echo "$?" > /work/seq_sta_$c.rc
   grep OT_POSTCTS_GATE /work/seq_sta_$c.log
  done
 fi
 chown -R 1000:1000 /work
 exit "$rc"
 '
done
