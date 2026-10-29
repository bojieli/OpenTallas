#!/bin/bash
# HBM-CORES-KITS-10: strap ECO on the kit ODBs (synth view for LEC/face_guard; V2 CTS start point; V1 GRT start point)
set -euo pipefail
W=/srv/opentallas-scratch2/claude/kits10-1029/ring
B=run/results/asap7/hbc_ot_hfd_coll_q2_hard_v8g__ring_ag/base
run() { docker run --rm --memory=16g -v $W:/w "${@:2}" openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/$1" 2>&1 | grep -v STA-1212; }
for v in v1 v2; do
  R=$W/$v/$B; [ -f $R/1_synth.odb.orig ] || { cp $R/1_synth.odb $R/1_synth.odb.orig; cp $R/1_synth.v $R/1_synth.v.orig; }
  run strap_eco.tcl -e ECO_IN=/w/$v/$B/1_synth.odb.orig -e ECO_OUT=/w/$v/$B/1_synth.odb
  run wv.tcl -e ECO_IN=/w/$v/$B/1_synth.odb -e ECO_V=/w/$v/$B/1_synth.v
done
R=$W/v2/$B; for s in 4_1_cts 4_cts; do [ -f $R/$s.odb.orig ] || cp $R/$s.odb $R/$s.odb.orig; done
run strap_eco.tcl -e ECO_IN=/w/v2/$B/4_cts.odb.orig -e ECO_OUT=/w/v2/$B/4_cts.odb -e ECO_FIRM=1
cp $R/4_cts.odb $R/4_1_cts.odb
R=$W/v1/$B; [ -f $R/5_1_grt.odb.orig ] || cp $R/5_1_grt.odb $R/5_1_grt.odb.orig
run strap_eco.tcl -e ECO_IN=/w/v1/$B/5_1_grt.odb.orig -e ECO_OUT=/w/v1/eco_in_grt.odb -e ECO_FIRM=1
echo ECO_ALL_DONE
