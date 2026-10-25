#!/bin/bash
cd /srv/opentallas-scratch/claude/wt/s81-kits-1024r-nodes
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
B=/srv/opentallas-scratch/claude/rtlc_bench/gunit; rm -rf $B; mkdir -p $B
( bash rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh $B/base 8 > $B/base.txt 2>&1; echo "rc=$?" >> $B/base.txt ) &
for m in L0 L1 L1C L1F L2 L3 L4 L5; do
 ( GUNIT_DEFS="-DOT_S81_VE_LOADSAFE5 -DOT_RTLC_MUT_$m" bash rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh $B/m$m 8 0 > $B/m$m.txt 2>&1; echo "rc=$?" >> $B/m$m.txt ) &
done
wait
