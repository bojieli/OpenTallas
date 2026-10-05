#!/bin/bash
# Runs every r6 bench case (list.txt + extra.txt) against the edited stream PC on ot-epyc1tb.
R=/srv/opentallas-scratch/claude/hbm-clock-loops/stream
cd $R/src; L=${LOGS:-logs-r8}; mkdir -p $R/$L
while read name args; do
  [ -z "$name" ] && continue
  ( RUN_DIR=$R/bench-$L/$name /srv/opentallas-scratch/admit.sh 2 -- tests/rtl/run_hbm_stream_bw.sh $args > $R/$L/$name.log 2>&1; echo "rc=$?" >> $R/$L/$name.log ) &
  sleep 1
done < results/rtl/hbm_clock_loops_20261004/stream/bench_cases.txt
wait
