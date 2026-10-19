#!/bin/bash
# MU-DIE-S81/LINECOL (10-19): after the MU-GEN mu1 cut build+idle (TOK, or relaunched here) -> SU L0/L2/L14/L20 replays of the
# line-slot-reserved programmes (prog_<L>_su, compiler claude/mu-die-s81-linecol-1019) -> dv_cut_replay check.
# cut_3S_ctl: gen with --idle-run + ks mod-4 sweep (chain_l0b.sh).  Usage: chain_lc.sh <cut> <idle ot-run pid | launch:MEM>
set -u
c=$1; P=$2
W=/home/ubuntu/wt/mu-die-s81-linecol-1019; T=/home/ubuntu/scratch/mu-die-s81/tok; S=/home/ubuntu/scratch/mu-die-s81/linecol
D=/srv/opentallas-scratch/claude/mu-die-s81-tok; DIE=$T/tree_mu/results/arch/s81_dv_1016/bind9/die.v.gz
exec >> $S/logs/chain_lc_$c.log 2>&1
IL=$T/logs/idle_$c.log
if [[ $P == launch:* ]]; then
  IL=$S/logs/idle_$c.log
  echo "$(date +%H:%M) relaunch idle build $c mem ${P#launch:}"
  /home/ubuntu/bin/ot-run --mem ${P#launch:} --dir $D -- env J=16 bash K_$c/run_dv_slice.sh K_$c out_${c}_idle +NCYC=2000 +TRACE=$D/out_${c}_idle/trace.txt > $IL 2>&1
else
  echo "$(date +%H:%M) chain_lc $c waiting on $P"; while kill -0 $P 2>/dev/null; do sleep 60; done
fi
H=$(grep -oE "RAN on [a-z0-9-]+ \(unit [^)]*\): exit [0-9]+" $IL | tail -1); rc=$(echo "$H" | awk '{print $NF}')
host=""; for h in $(echo "$H" | awk '{print $3}') ot-epyc8 ot-epyc5 ot-epyc6 ot-epyc4 ot-epyc7; do ssh $h "ls $D/out_${c}_idle/obj/sim" >/dev/null 2>&1 && { host=$h; break; }; done
echo "$(date +%H:%M) idle: $H obj host $host"
[ "$rc" = 0 ] && [ -n "$host" ] || { echo "IDLE FAIL/no obj -> stop"; exit 1; }
mkdir -p $S/runs/idle_$c; rsync -a $host:$D/out_${c}_idle/status $host:$D/out_${c}_idle/trace.txt $S/runs/idle_$c/
RS=""
cd $W
for L in L0 L2 L14 L20; do
  if [ "$c" = cut_3S_ctl ]; then
    r0=R_${c}_${L}_su_ks0
    timeout 900 python3 tools/s81_dv/dv_cut_replay.py gen --die-v $DIE --prog $S/prog_${L}_su --cut $T/cuts/$c --out $S/R/$r0 --idle-run $S/runs/idle_$c > $S/logs/gen_${c}_${L}_ks0.log 2>&1 || { echo "gen $r0 FAIL: $(tail -n1 $S/logs/gen_${c}_${L}_ks0.log)"; continue; }
    ks0=$(python3 -c "import json;print(json.load(open('$S/R/$r0/replay.json'))['host_boot']['ks'])"); RS="$RS $r0"
    for d in 1 2 3; do r=R_${c}_${L}_su_ks$d
      timeout 900 python3 tools/s81_dv/dv_cut_replay.py gen --die-v $DIE --prog $S/prog_${L}_su --cut $T/cuts/$c --out $S/R/$r --idle-run $S/runs/idle_$c --ks $((ks0 + d)) > $S/logs/gen_${c}_${L}_ks$d.log 2>&1 && RS="$RS $r"
    done
  else RS="$RS R_${c}_${L}_su"; fi
done
echo "$(date +%H:%M) replays $RS"
pids=""
for r in $RS; do
  rsync -a $S/R/$r $host:$D/lc/
  n=$(python3 -c "import json;print(json.load(open('$S/R/$r/replay.json'))['ncyc'] + 200)")
  ( /home/ubuntu/bin/ot-run --mem 8 --hosts $host --dir $D -- env OBJ=$D/out_${c}_idle/obj bash K_$c/run_dv_slice.sh K_$c lc/out_$r \
      +IN=$D/lc/$r/in.txt +OUT=$D/lc/$r/out.txt +NCYC=$n +TRACE=$D/lc/out_$r/trace.txt > $S/logs/run_$r.log 2>&1
    mkdir -p $S/runs/out_$r; rsync -a --exclude obj $host:$D/lc/out_$r/ $S/runs/out_$r/
    cd $W && timeout 900 python3 tools/s81_dv/dv_cut_replay.py check --replay $S/R/$r --run $S/runs/out_$r --out $S/runs/out_$r/check.json > $S/logs/check_$r.log 2>&1
    echo "$(date +%H:%M) $r: $(tail -n 1 $S/logs/check_$r.log)" ) &
  pids="$pids $!"
done
wait $pids
echo "$(date +%H:%M) chain_lc $c DONE"
