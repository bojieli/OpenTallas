#!/bin/bash
# launch.sh NAME NICK : ot-run the R2 kit (on epyc1)
O=/srv/opentallas-scratch2/claude/qc-su-lat
nohup ~/.local/bin/ot-run --mem 32 --threads 8 --no-spill --dir $O/$1 -- $O/r2s/run_r2.sh $O/$1 $2 > $O/../qc-su-lat-r2-otrun_$1.log 2>&1 &
echo launched $1 pid $!
