#!/bin/bash
# PART-CAP: route one capacity kit with the production ref_route.sh and sample container CPU / memory every 30 s.
# usage (on the host, from anywhere): run_one.sh NAME OUTROOT     (worktree = ~/wt/part-cap)
set -u
NAME=$1; OUT=$2; WT=${PART_CAP_WT:-$HOME/wt/part-cap}
export CORNER=${CORNER:-TC}
mkdir -p $OUT/$NAME
(
  while true; do
    for c in $(docker ps -q 2>/dev/null); do
      if docker inspect -f '{{range .Mounts}}{{.Source}} {{end}}' $c 2>/dev/null | grep -q "$OUT/$NAME/"; then
        docker stats --no-stream --format '{{.CPUPerc}} {{.MemUsage}}' $c 2>/dev/null \
          | sed "s|^|$(date +%s) $c |" >> $OUT/$NAME/docker_stats.log
      fi
    done
    sleep 30
  done
) &
SAMPLER=$!
# kit-name suffix _tnsK = ORFS repair_timing -repair_tns K (OT_TNS_END_PERCENT; the production default is 100)
case $NAME in *_tns*) export OT_TNS_END_PERCENT=${NAME##*_tns};; esac
echo "OT_TNS_END_PERCENT=${OT_TNS_END_PERCENT:-100} NC from kit" >> $OUT/$NAME/STATUS
/usr/bin/time -v -o $OUT/$NAME/time_v.txt env SRC=$WT bash $WT/tools/ref_tile/ref_route.sh \
  $WT/results/arch/part_capacity_1024/kits/$NAME/kit.env $NAME $OUT
rc=$?
kill $SAMPLER
echo "rc=$rc" >> $OUT/$NAME/STATUS
exit $rc
