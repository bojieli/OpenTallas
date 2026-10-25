#!/bin/bash
K=$1; TO=$2; T=$(dirname $(readlink -f $0)); R=$(ls -d $K/run/results/asap7/*/base | head -1); RR=${R#$K}
docker run --rm --cpus=2 --memory=8g -v $K:/work:ro -v $T:/t:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
 PLIBS=\"\$(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/w FLOW_VARIANT=base print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')\" \
 ODB=/work$RR/4_cts.odb SDC=/work$RR/4_cts.sdc PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 TO='$TO' openroad -exit /t/onepath.tcl 2>&1 | grep -v WARNING"
