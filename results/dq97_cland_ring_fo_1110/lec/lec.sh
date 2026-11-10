#!/bin/bash
# usage: lec.sh RTLDIR OUTDIR [MUTANT_DEFINE]   runs yosys (ORFS image) equiv_make/induct gold vs gate
R=$1; O=$2; MUT=$3; mkdir -p $O; H=$(cd $(dirname $0) && pwd)
docker run --rm --memory=24g --memory-swap=24g --name dq97lec_$$ --user $(id -u):$(id -g) -v $R:/rtl:ro -v $H:/h:ro -v $O:/o \
  openroad/orfs:asap7lock bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /o; python3 /h/mkys.py ${MUT:+$MUT} > lec.ys; yosys -q -l lec.log -s lec.ys; echo YOSYS_RC=\$?" 2>&1 | tail -3
