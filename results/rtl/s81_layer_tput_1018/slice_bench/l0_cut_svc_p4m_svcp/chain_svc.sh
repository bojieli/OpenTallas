#!/bin/bash
# TW3-S81/LAYERS/SVCP4M (10-19): cut_svc on bind_p4m_g8r_svcp (G8R2 p4m + svc P lane pr_09_07, PPATH on):
# build + idle 2000 (ot-run auto host pick, --mem 400) -> L0 replay run on the obj host (OBJ reuse, 8 GB) -> dv_cut_replay check.
# The L0 replay (R_cut_svc_L0, ncyc 11,639, 195 checks, not stale) is generated before launch from prog_L0 (compiler fcc8bf542).
set -u
W=/home/ubuntu/wt/tw3-s81-svcp4m; S=/home/ubuntu/scratch/tw3-s81-svcp4m; D=/srv/opentallas-scratch/claude/tw3-s81-svcp4m
c=cut_svc; R=R_cut_svc_L0; L=$S/logs/chain_$c.log; mkdir -p $S/logs; exec >> $L 2>&1
echo "$(date +%H:%M) chain $c: build+idle"
/home/ubuntu/bin/ot-run --mem 400 --threads 16 --dir $D -- env J=16 bash K_$c/run_dv_slice.sh K_$c out_${c}_idle \
  +NCYC=2000 +TRACE=$D/out_${c}_idle/trace.txt > $S/logs/idle_$c.log 2>&1
H=$(grep -oE "RAN on [a-z0-9-]+ \(unit [^)]*\): exit [0-9]+" $S/logs/idle_$c.log | tail -1)
echo "$(date +%H:%M) idle done: $H"
host=$(echo "$H" | awk '{print $3}'); rc=$(echo "$H" | awk '{print $NF}')
for h in $host ot-epyc5 ot-epyc4; do ssh $h "test -x $D/out_${c}_idle/obj/sim" 2>/dev/null && { host=$h; break; }; done; echo "obj host $host"
mkdir -p $S/runs/idle_$c; rsync -a $host:$D/out_${c}_idle/status $host:$D/out_${c}_idle/build.time $S/runs/idle_$c/ 2>/dev/null
cat $S/runs/idle_$c/status 2>/dev/null
[ "$rc" = "0" ] || { echo "IDLE FAIL ($H) -> stop (check $S/logs/idle_$c.log, $host:$D/out_${c}_idle)"; exit 1; }
n=$(python3 -c "import json;print(json.load(open('$S/$R/replay.json'))['ncyc'] + 200)")
/home/ubuntu/bin/ot-run --mem 8 --hosts $host --dir $D -- env OBJ=$D/out_${c}_idle/obj bash K_$c/run_dv_slice.sh K_$c out_$R \
  +IN=$D/$R/in.txt +OUT=$D/$R/out.txt +NCYC=$n +TRACE=$D/out_$R/trace.txt > $S/logs/run_$R.log 2>&1
echo "$(date +%H:%M) run: $(grep -oE 'RAN on .*exit [0-9]+' $S/logs/run_$R.log | tail -1)"
mkdir -p $S/runs/out_$R; rsync -a --exclude obj $host:$D/out_$R/ $S/runs/out_$R/
cd $W && timeout 900 python3 tools/s81_dv/dv_cut_replay.py check --replay $S/$R --run $S/runs/out_$R --out $S/runs/out_$R/check.json \
  > $S/logs/check_$R.log 2>&1
echo "$(date +%H:%M) $R: $(tail -n 1 $S/logs/check_$R.log)"
echo "$(date +%H:%M) chain $c DONE"
