#!/bin/bash
# run GRT of an already generated coupon dir O (ot-run on intel2 = localhost)
O=$1
~/.local/bin/ot-run --mem 24 --threads 8 --hosts localhost --dir $O -- docker run --rm --name d8-cpn-$(basename $O)-$$ --cpus 8 --memory 24g --memory-swap 24g -v $O:/work -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /work/grt/grt.tcl > /work/grt/route.log 2>&1; rc=\$?; chown -R \$HUID:\$HGID /work; exit \$rc" > $O.run.log 2>&1
echo COUPON_RC $? >> $O.run.log
