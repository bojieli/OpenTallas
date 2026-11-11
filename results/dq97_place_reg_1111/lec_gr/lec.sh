#!/bin/bash
# usage: lec.sh RTLDIR OUTDIR K   yosys equiv_make/induct gold (no PLACEREP) vs gate (PLACEREP 1), strap_k = K
R=$1; O=$2; K=$3; mkdir -p $O; H=$(cd $(dirname $0) && pwd)
docker run --rm --memory=24g --memory-swap=24g --name dq97lecp_$$ --user $(id -u):$(id -g) -v $R:/rtl:ro -v $H:/h:ro -v $O:/o \
  openroad/orfs:asap7lock bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /o; python3 /h/mkys.py $K > lec_k$K.ys; yosys -q -l lec_k$K.log -s lec_k$K.ys; echo K=$K YOSYS_RC=\$?" 2>&1 | tail -3
