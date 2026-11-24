#!/bin/bash
# usage: regen_run.sh REGEN_DIR MODULE
R=$1; M=$2; IMG=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
for c in TT FF; do
  docker run --rm --name ctb_rg_${M:0:20}_${c}_$$ -e OT_C=$c -e OT_MOD=$M -v $R:/r -v $(dirname $0)/regen.tcl:/regen.tcl:ro $IMG \
    /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /regen.tcl > $R/regen_$c.log 2>&1
  echo "$M $c rc $? $(grep -c 'OT_REGEN WROTE' $R/regen_$c.log) $(grep -m1 -E '^\[ERROR' $R/regen_$c.log)"
done
