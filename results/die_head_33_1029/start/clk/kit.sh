#!/bin/bash
# DIE-HEAD-26: ot_clk kit for HEAD hk4 (usage: dh25_kit.sh TAG CONFIG)
T=$1; CFG=$2; R=/srv/opentallas-scratch2/claude/die-head-33/start/clk; W=/srv/opentallas-scratch2/claude/wt/die-head-33-start
rm -rf $R/kit_$T; cd $W
systemd-run --user --scope -p MemoryMax=32G python3 tools/clk/ot_clk.py kit $CFG --out $R/kit_$T --workers 24
echo KIT_${T}_RC $? $(date)
