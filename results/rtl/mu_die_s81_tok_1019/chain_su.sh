#!/bin/bash
# MU-DIE-S81/TOK (10-19): single-user L0/L2/L14/L20 replays on a MU-GEN cut build (OBJ reuse) -> dv_cut_replay check.
# Usage: chain_su.sh <cut> <idle ot-run pid>
set -u
c=$1; P=$2
W=/home/ubuntu/wt/mu-die-s81-tok; S=/home/ubuntu/scratch/mu-die-s81/tok; D=/srv/opentallas-scratch/claude/mu-die-s81-tok
exec >> $S/logs/chain_su_$c.log 2>&1
echo "$(date +%H:%M) chain_su $c waiting on $P"
while kill -0 $P 2>/dev/null; do sleep 60; done
H=$(grep -oE "RAN on [a-z0-9-]+ \(unit [^)]*\): exit [0-9]+" $S/logs/idle_$c.log | tail -1); rc=$(echo "$H" | awk '{print $NF}')
host=""; for h in $(echo "$H" | awk '{print $3}') ot-epyc8 ot-epyc5 ot-epyc6 ot-epyc4 ot-epyc7; do ssh $h "ls $D/out_${c}_idle/obj/sim" >/dev/null 2>&1 && { host=$h; break; }; done
echo "$(date +%H:%M) idle: $H obj host $host"
[ "$rc" = 0 ] && [ -n "$host" ] || { echo "IDLE FAIL/no obj -> stop"; exit 1; }
mkdir -p $S/runs/idle_$c; rsync -a $host:$D/out_${c}_idle/status $host:$D/out_${c}_idle/trace.txt $S/runs/idle_$c/
pids=""
for L in L0 L2 L14 L20; do r=R_${c}_${L}_su
  rsync -a $S/R/$r $host:$D/
  n=$(python3 -c "import json;print(json.load(open('$S/R/$r/replay.json'))['ncyc'] + 200)")
  ( /home/ubuntu/bin/ot-run --mem 8 --hosts $host --dir $D -- env OBJ=$D/out_${c}_idle/obj bash K_$c/run_dv_slice.sh K_$c out_$r \
      +IN=$D/$r/in.txt +OUT=$D/$r/out.txt +NCYC=$n +TRACE=$D/out_$r/trace.txt > $S/logs/run_$r.log 2>&1
    mkdir -p $S/runs/out_$r; rsync -a --exclude obj $host:$D/out_$r/ $S/runs/out_$r/
    cd $W && timeout 900 python3 tools/s81_dv/dv_cut_replay.py check --replay $S/R/$r --run $S/runs/out_$r --out $S/runs/out_$r/check.json > $S/logs/check_$r.log 2>&1
    echo "$(date +%H:%M) $r: $(tail -n 1 $S/logs/check_$r.log)" ) &
  pids="$pids $!"
done
wait $pids
echo "$(date +%H:%M) chain_su $c DONE"
