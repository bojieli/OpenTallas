#!/bin/bash
# PATH-QC-RP1-F59 review dump (docker, ORFS image): rdump (f6_rdump.py) on 3_place + 5_1_grt, TT clock dump (ckdump.tcl) on 5_1_grt
K=$(cd "$1" && pwd); NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' "$K/config.mk"); B=/work/run/results/asap7/$NICK/base
mkdir -p $K/review
docker run --rm --name rp1rev-$(basename $K)-$$ --memory=8g --memory-swap=8g -v $K:/work -w /work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
 for s in 3_place 5_1_grt; do ODB=$B/\$s.odb OUT=/work/review/rdump_\$s.tsv openroad -python -exit /work/f6_rdump.py; done; \
 MC=TT ODB=$B/5_1_grt.odb SDC=$B/5_1_grt.sdc OUT=/work/review/ck_TT.tsv /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/ckdump.tcl > /work/review/ckdump.log 2>&1; \
 cp $B/ot_macro_pin_flops.txt /work/review/mpf.txt; chown -R $(id -u):$(id -g) /work/review"
tail -2 $K/review/ckdump.log
