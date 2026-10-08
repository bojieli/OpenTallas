#!/bin/bash
# usage: check_io.sh <route dir>: IO re-timed against the measured per-corner insertion (150 ps die skew, 100 ps wire);
# exit 0 iff every IO slack >= +15 ps at SS (setup); FF hold at the pins is the die-context check.
D=$1; H=$(cd "$(dirname "$0")/../dsrom_su_softmax_r5" && pwd)
bash $H/io_budget.sh $D/work/orfs $D/io 150 100 | tee $D/io_budget.txt
python3 - <<P
import re,sys
bad=0
for l in open("$D/io_budget.txt"):
    if not l.startswith("ss "): continue      # INPUT/OUTPUT hold at FF is left to the die context (stations' min-delay credit)
    for k,v in re.findall(r"OT_IO_(IN|OUT) (\S+)",l):
        if v!="INF" and float(v)<15: bad+=1
sys.exit(1 if bad else 0)
P
