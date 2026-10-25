#!/bin/bash
cd /srv/opentallas-scratch/claude/wt/s81-kits-1024r-nodes; export PATH=$HOME/.local/opentallas-tools/bin:$PATH J=8
B=/srv/opentallas-scratch2/claude/rtlc2/xfin
run(){ n=$1; shift; ( "$@" > $B/$n.txt 2>&1; echo "rc=$?" >> $B/$n.txt ) & }
run eng_base bash tools/s81_dv/xfin_eng_bench.sh $B/eng_base base 0 0 1
run eng_base2 bash tools/s81_dv/xfin_eng_bench.sh $B/eng_base2 base 1 2 2
run eng_rtlc bash tools/s81_dv/xfin_eng_bench.sh $B/eng_rtlc rtlcxfin 0 0 1
run eng_tag bash tools/s81_dv/xfin_eng_bench.sh $B/eng_tag mutetag 0 0 1
run norm_base bash tools/s81_dv/norm16_bench.sh $B/norm_base base xfin
run norm_leaf bash tools/s81_dv/norm16_bench.sh $B/norm_leaf mutleaf xfin
wait
