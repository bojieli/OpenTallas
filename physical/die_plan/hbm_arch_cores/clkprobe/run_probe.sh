#!/bin/bash
# run_probe.sh RUNDIR OUTDIR : read-only docker probe of 4_cts.odb (diagnostic, memory-capped)
K=$1; O=$2; mkdir -p $O; T=$(dirname $(readlink -f $0))
R=$(ls -d $K/run/results/asap7/*/base | head -1); RR=${R#$K}
docker run --rm --name clkprobe-$(basename $O)-$$ --cpus=4 --memory=12g --memory-swap=12g -v $K:/work:ro -v $O:/out -v $T:/t:ro \
 -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
 PLIBS=\"\$(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/w FLOW_VARIANT=base print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')\" \
 ODB=/work$RR/4_cts.odb SDC=/work$RR/4_cts.sdc PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 OUT=/out openroad -exit /t/clkprobe.tcl > /out/probe.log 2>&1; chown -R $(id -u):$(id -g) /out; tail -3 /out/probe.log"
