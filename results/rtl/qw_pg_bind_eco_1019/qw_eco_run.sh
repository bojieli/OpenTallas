#!/bin/bash
# ROOT4 10-19: PG-bind-only ECO (S81 method, results/rtl/s81_pg_bind_eco_1019) on the 17 Qwen closed views of audit 0ea3ca6ba
T=/home/ubuntu/.claude/jobs/33555330/tmp/root4
while read name host root base; do
  echo "$name $host" ; bash /home/ubuntu/scratch/s81-native-pg/launch.sh $name $host $root $base > $T/eco_$name.log 2>&1 &
  while [ $(jobs -r | wc -l) -ge 6 ]; do sleep 5; done
done < $T/qw_eco_list.txt
wait
echo ALLDONE
