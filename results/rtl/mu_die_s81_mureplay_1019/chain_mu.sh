#!/bin/bash
# MU-DIE-S81/MUREPLAY (10-19): cut_7 MU replays (dv_cut_replay gen --mu) + single-user references on TOK's cut_7 build
# (OBJ reuse: same netlist, same kit), Verilator 5.050 via ot-run; then check + mucheck locally.
# Usage: chain_mu.sh <TOK idle ot-run pid>
set -u
P=$1; c=cut_7
W=/home/ubuntu/wt/mu-die-s81-mureplay; T=/home/ubuntu/scratch/mu-die-s81/tok; M=/home/ubuntu/scratch/mu-die-s81/mureplay
D=/srv/opentallas-scratch/claude/mu-die-s81-tok
exec >> $M/logs/chain_mu.log 2>&1
echo "$(date +%H:%M) chain_mu waiting on $P"
while kill -0 $P 2>/dev/null; do sleep 60; done
H=$(grep -oE "RAN on [a-z0-9-]+ \(unit [^)]*\): exit [0-9]+" $T/logs/idle_$c.log | tail -1); rc=$(echo "$H" | awk '{print $NF}')
host=""; for h in $(echo "$H" | awk '{print $3}') ot-epyc8 ot-epyc5 ot-epyc6 ot-epyc4 ot-epyc7; do ssh $h "ls $D/out_${c}_idle/obj/sim" >/dev/null 2>&1 && { host=$h; break; }; done
echo "$(date +%H:%M) idle: $H obj host $host"
[ "$rc" = 0 ] && [ -n "$host" ] || { echo "IDLE FAIL/no obj -> stop"; exit 1; }
ssh $host "mkdir -p $D/mureplay"
run() { r=$1; n=$2
  rsync -a $M/R/$r $host:$D/mureplay/
  /home/ubuntu/bin/ot-run --mem 8 --hosts $host --dir $D -- env OBJ=$D/out_${c}_idle/obj bash K_$c/run_dv_slice.sh K_$c mureplay/out_$r \
      +IN=$D/mureplay/$r/in.txt +OUT=$D/mureplay/$r/out.txt +NCYC=$n +TRACE=$D/mureplay/out_$r/trace.txt > $M/logs/run_$r.log 2>&1
  mkdir -p $M/runs/out_$r; rsync -a --exclude obj $host:$D/mureplay/out_$r/ $M/runs/out_$r/
  echo "$(date +%H:%M) $r ran: $(tail -n 2 $M/logs/run_$r.log | tr '\n' ' ')"; }
nc() { python3 -c "import json;print(json.load(open('$M/R/$1/replay.json'))['ncyc'] + 200)"; }
pids=""
# single-user references, run to the MU window end (window + t0 + 50)
run R_cut_7_L0_su $((21312 + 100 + 250)) & pids="$pids $!"
run R_cut_7_L2_su $((42624 + 100 + 250)) & pids="$pids $!"
for r in R_cut_7_L0_mu012 R_cut_7_L0_mu012_drop2 R_cut_7_L0_mu012_off1 R_cut_7_L2_muA02 R_cut_7_L2_muA02_drop2 R_cut_7_L2_muB13; do
  run $r $(nc $r) & pids="$pids $!"
done
wait $pids
cd $W
for L in L0 L2; do timeout 900 python3 tools/s81_dv/dv_cut_replay.py check --replay $M/R/R_cut_7_${L}_su --run $M/runs/out_R_cut_7_${L}_su \
  --out $M/runs/out_R_cut_7_${L}_su/check.json > $M/logs/check_R_cut_7_${L}_su.log 2>&1; echo "$(date +%H:%M) SU $L: $(tail -n1 $M/logs/check_R_cut_7_${L}_su.log)"; done
for r in R_cut_7_L0_mu012 R_cut_7_L0_mu012_drop2 R_cut_7_L0_mu012_off1; do
  timeout 1800 python3 tools/s81_dv/dv_cut_replay.py mucheck --replay $M/R/$r --run $M/runs/out_$r --su-replay $M/R/R_cut_7_L0_su \
    --su-run $M/runs/out_R_cut_7_L0_su --out $M/runs/out_$r/mucheck.json > $M/logs/mucheck_$r.log 2>&1; echo "$(date +%H:%M) $r: $(tail -n1 $M/logs/mucheck_$r.log)"; done
for r in R_cut_7_L2_muA02 R_cut_7_L2_muA02_drop2; do
  timeout 1800 python3 tools/s81_dv/dv_cut_replay.py mucheck --replay $M/R/$r --run $M/runs/out_$r --su-replay $M/R/R_cut_7_L2_su \
    --su-run $M/runs/out_R_cut_7_L2_su --out $M/runs/out_$r/mucheck.json > $M/logs/mucheck_$r.log 2>&1; echo "$(date +%H:%M) $r: $(tail -n1 $M/logs/mucheck_$r.log)"; done
r=R_cut_7_L2_muB13; timeout 1800 python3 tools/s81_dv/dv_cut_replay.py mucheck --replay $M/R/$r --run $M/runs/out_$r --out $M/runs/out_$r/mucheck.json \
  > $M/logs/mucheck_$r.log 2>&1; echo "$(date +%H:%M) $r: $(tail -n1 $M/logs/mucheck_$r.log)"
echo "$(date +%H:%M) chain_mu DONE"
