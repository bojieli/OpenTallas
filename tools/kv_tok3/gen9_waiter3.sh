#!/bin/bash
# KV-TOK3 10-19: GEN9 token-vehicle waiter WITH the startup repair (replaces KV-TOK2's gen9_waiter.sh, which watched the
# deleted 7f9501c62 run on the wrong host and staged the unrepaired boot-word fixture).
# Every 5 min (<= 12 h): find the newest STRICT GEN9 KV run kvs14r-*-gen9s* on any fleet host that has NOT PREP FAILed and
# holds the vehicle inputs; stage the repaired fixture (kv-tok3 pickup3: gen_kva_authority.py + N-step identity adapter)
# into a run-unique dir on THAT host (data locality), launch WSQK / P0 / P1 (cases u1 u4cal u4pack) via unpinned ot-run.
set -u
L=/home/ubuntu/artifacts/kv-tok3-1019
P=$L/pickup3
B=/srv/opentallas-scratch/claude/qwen-kvsys
HOSTS="ot-epyc5 ot-epyc6 ot-epyc4 ot-epyc7 ot-epyc8"
exec >> "$L/gen9_waiter3.log" 2>&1
echo "$(date -Is) waiter3 start pid $$"
for ((i=0;i<144;i++)); do
 for h in $HOSTS; do
  R=$(timeout 60 ssh -o ControlPath=none $h "for r in \$(ls -dt $B/kvs14r-*-gen9s* 2>/dev/null); do
      [ -d \$r ] || continue; grep -q 'PREP FAIL' \$r/STATUS.log 2>/dev/null && continue
      test -s \$r/port_bind_v2/die_bound.v && test -s \$r/port_bind_v2/port_bind_v2.json && test -s \$r/case_kv/relay_stages.json \
        && test -s \$r/case_kv/boot_ages.json && test -s \$r/relay_check.json && { echo \$r; break; }; done" 2>/dev/null)
  [ -n "$R" ] || continue
  N=$(basename $R); K=$B/wt-$N; D=/srv/opentallas-scratch/claude/kv-tok3-1019/veh_$N
  echo "$(date -Is) GEN9 strict inputs available on $h: $R"
  timeout 60 ssh -o ControlPath=none $h "test -d $K" || { echo "no source tree $K on $h"; continue; }
  timeout 60 ssh -o ControlPath=none $h "test -e $D" && { echo "REFUSED: $D exists (already launched)"; exit 4; }
  timeout 60 ssh -o ControlPath=none $h "mkdir -p $D" && timeout 300 rsync -a -e 'ssh -o ControlPath=none' $P/tools $P/lint_fixture.sh $L/cases_stk.txt $h:$D/ || { echo "stage failed"; exit 5; }
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
