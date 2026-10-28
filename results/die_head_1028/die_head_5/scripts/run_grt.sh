#!/bin/bash
# DIE-HEAD-5 real-netlist die GRT incl clock, corner $1
C=$1; G=/srv/opentallas-scratch2/claude/die-head-5/grt
docker run --rm --name dh5-grt-$C --memory=96g --memory-swap=96g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM   -v $G/kit:/work:ro -v $G/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
