#!/bin/bash
# HBM-CLKLOC-7: same GRT as a3e6s run_grt.tcl (deterministic: TT rerun matched byte-for-byte) with FF libraries -> tree_grt_FF.txt
O=$(cd $(dirname $0) && pwd); N=$(basename $O)
docker run --rm --name clkloc7-meshff-$N --memory=100g --memory-swap=100g --cpus=16 -e ADJ=0.4 -e LC=FF -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O:/o openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 16 -exit /o/grt_tf.tcl > /o/grt_ff.log 2>&1; echo EXIT \$? >> /o/grt_ff.log; chown -R 1000:1000 /o"
