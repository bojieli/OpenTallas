#!/bin/bash
# TAKEOVER3 source proposal only: activate for one explicit reviewed GEN9 run.
# Never scan or silently retarget to a newer/older source. No launch authorized by this file.
set -u
if [ "$#" -ne 2 ]; then
 echo "usage: $0 <data-host> <reviewed-kvs14r-HASH-gen9s-NAME>" >&2; exit 64
fi
DATA_HOST=$1
RUN_NAME=$2
case "$DATA_HOST" in ot-epyc[4-8]) ;; *) echo "REFUSED: invalid data host" >&2; exit 64;; esac
case "$RUN_NAME" in kvs14r-*-gen9s*) ;; *) echo "REFUSED: not a strict GEN9 run name" >&2; exit 64;; esac
case "$RUN_NAME" in *[!a-zA-Z0-9_.-]*) echo "REFUSED: unsafe run name" >&2; exit 64;; esac
L=/home/ubuntu/artifacts/kv-tok3-1019
P=$L/pickup3
B=/srv/opentallas-scratch/claude/qwen-kvsys
HOSTS="$DATA_HOST"
exec >> "$L/gen9_waiter3.log" 2>&1
echo "$(date -Is) explicit waiter3 start pid $$ run $RUN_NAME host $DATA_HOST"
for ((i=0;i<144;i++)); do
 for h in $HOSTS; do
  R=$B/$RUN_NAME
  if timeout 60 ssh -o ControlPath=none "$h" "test -s $R/STATUS.log && grep -q 'PREP FAIL' $R/STATUS.log"; then
   echo "$(date -Is) REFUSED: exact run PREP FAIL $h:$R"; exit 3
  fi
  timeout 60 ssh -o ControlPath=none "$h" "test -s $R/port_bind_v2/die_bound.v && test -s $R/port_bind_v2/port_bind_v2.json && test -s $R/case_kv/relay_stages.json && test -s $R/case_kv/boot_ages.json && test -s $R/relay_check.json" || continue
  N=$(basename $R); K=$B/wt-$N; D=/srv/opentallas-scratch/claude/kv-tok3-1019/veh_$N
  echo "$(date -Is) GEN9 strict inputs available on $h: $R"
  timeout 60 ssh -o ControlPath=none $h "test -d $K" || { echo "no source tree $K on $h"; continue; }
  timeout 60 ssh -o ControlPath=none $h "test -e $D" && { echo "REFUSED: $D exists (already launched)"; exit 4; }
  timeout 60 ssh -o ControlPath=none $h "mkdir $D" && timeout 300 rsync -a -e 'ssh -o ControlPath=none' $P/tools $L/cases_stk.txt $h:$D/ || { echo "stage failed"; exit 5; }
  for v in WSQK:128 P0:300 P1:300; do
   /home/ubuntu/bin/ot-run --mem "${v#*:}" --threads 16 --no-spill --dir "$D" -- bash -lc "ulimit -s unlimited; KVA_VFLAGS='-fno-dfg -fno-inline' bash tools/qwen_layerbench/kva_vehicle.sh ${v%:*} $R $K g9n/${v%:*} cases_stk.txt" > "$L/g9n_${N}_${v%:*}.out" 2>&1 &
   sleep 3
  done
  echo "$(date -Is) launched WSQK/P0/P1 for $N in $h:$D/g9n (clients $L/g9n_${N}_*.out)"
  wait
  echo "$(date -Is) GEN9 vehicle clients ended; inspect each run_<case>.log with identity_verdict.parse_verdict"
  exit 0
 done
 sleep 300
done
echo "$(date -Is) no strict GEN9 inputs within 12 h; no vehicles launched"
exit 1
