#!/bin/bash
# usage: lec_rs.sh NEW_RTLDIR OLD_RTLDIR OUTDIR MODE(rs|def) [DEFINE ...]   yosys (ORFS image) equiv_make/induct
R=$1; RO=$2; O=$3; MODE=$4; shift 4; mkdir -p $O; H=$(cd $(dirname $0) && pwd)
docker run --rm --memory=8g --memory-swap=8g --name dq97lecrs_$$ --user $(id -u):$(id -g) -v $R:/rtl:ro -v $RO:/rtl_old:ro -v $H:/h:ro -v $O:/o \
  openroad/orfs:asap7lock bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /o; python3 /h/mkys_rs.py $MODE $* > lec.ys; yosys -q -l lec.log -s lec.ys; echo YOSYS_RC=\$?" 2>&1 | tail -3
