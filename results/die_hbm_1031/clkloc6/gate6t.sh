#!/bin/bash
# HBM-CLKLOC-6: gate6 + per-tag contract breakdown (diagnostic wrapper bytag.py). usage: gate6t.sh PROOF OUT
R=/srv/opentallas-scratch2/claude/hbm-clkloc-1; ulimit -v 96000000
python3 $R/bytag.py $2.bytag.json -- $1 --plan $R/in/d44g/die_plan.json --out $2 --cppr-lca --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv2 --nominal-arrival single > $2.log 2>&1; echo "rc $? $(date)" >> $2.log
