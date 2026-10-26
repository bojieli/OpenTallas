#!/bin/bash
cd /srv/opentallas-scratch/claude/wt/s81-kits-1024r-nodes
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
B=/srv/opentallas-scratch2/claude/rtlc2/gunit; rm -rf $B; mkdir -p $B
( bash rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh $B/base 8 > $B/base.txt 2>&1; echo "rc=$?" >> $B/base.txt ) &
for m in L5 L5P; do
 ( GUNIT_DEFS="-DOT_S81_VE_LOADSAFE5 -DOT_RTLC_MUT_$m" bash rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh $B/m$m 8 0 > $B/m$m.txt 2>&1; echo "rc=$?" >> $B/m$m.txt ) &
done
wait
