#!/bin/bash
# usage: pgrun.sh KIT WORKDIR [GUARD] [TWO=1] -- run the kit's pregrt_ff_hold.tcl on a COPY of its 4_cts.odb (private prototype)
set -uo pipefail
K=$1; mkdir -p $2; W=$(realpath $2); G=${3:-25}; TWO=${4:-1}
D=$(basename $(dirname $(ls -d $K/run/results/asap7/*/base)))
cp $K/run/results/asap7/$D/base/4_cts.odb $W/4_cts.odb
TL='TLIBS="$($M print-TC_LIB_FILES 2>/dev/null | sed -n "s/^TC_LIB_FILES *[:=] *//p")"'; [ "$TWO" = 1 ] || TL=
docker run --rm --name ht1_pg_$$ --cpus=${CPUS:-16} --memory=${MEMG:-48}g -v $K:/work -v $W:/t0 -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base'; g() { sed -n \"s/^export \$1 = //p\" /work/config.mk; }; PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')\" $TL ODB=/t0/4_cts.odb SDC=/work/run/results/asap7/$D/base/4_cts.sdc PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 OT_VCLK_TT=\$(g OT_VCLK_TT) OT_VCLK_FF=\$(g OT_VCLK_FF) OT_HOLD_IN_MIN=\$(g OT_HOLD_IN_MIN) OT_HOLD_OUT_MIN=\$(g OT_HOLD_OUT_MIN) OT_TAP_WINDOW=\$(g OT_TAP_WINDOW) OT_PREGRT_HOLD_GUARD=$G LAYER_PARASITICS_FILE=\$(g LAYER_PARASITICS_FILE) openroad -exit /work/pregrt_ff_hold.tcl" > $W/pg.log 2>&1
echo rc $?; grep -n -E "OT_PREGRT|Error|ERROR|RSZ-00(32|66|46)" $W/pg.log | cut -c1-320
