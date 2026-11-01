#!/bin/bash
O=$(cd $(dirname $0) && pwd)
docker run --rm --name hbmhm6-drtc-NW-$$ --memory=200g --memory-swap=200g --cpus=16 -e GSTEP=${GSTEP:-5130} -e ENDIT=${ENDIT:-20} -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O:/o openroad/orfs:asap7lock bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
/usr/bin/time -v openroad -no_init -threads 16 -exit /o/drt.tcl > /o/drt.log 2>&1; echo EXIT \$? >> /o/drt.log
chown -R 1000:1000 /o"
