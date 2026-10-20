#!/usr/bin/env bash
# VEH-FMT-COLL2/COLL (10-19): wait for the SW-slice binary (sw2 on ot-epyc4 = TOK-HBM-VEH sw5, or the sw5e hedge on
# ot-epyc5), then run the 4 COLL.GROUP_REDUCE_MCAST on-die-phase replays (DS L0/L2/L3/L14) with REUSE=1, 8 at a time.
# Results: ~/scratch/veh-coll2-coll/results.txt (name host SLICE_PASS/FAIL checks), per-run logs in <base>/out_<name>/run.log
S=/home/ubuntu/scratch/veh-coll2-coll; RES=$S/results.txt
B4=/srv/opentallas-scratch/claude/layerbench-hbm/sw2; B5=/srv/opentallas-scratch/claude/layerbench-hbm/sw5e
for i in $(seq 1 600); do
  if ssh ot-epyc4 "test -x $B4/out/obj/Vtb_hbm_slice"; then H=ot-epyc4; D=$B4; break; fi
  if ssh ot-epyc5 "test -x $B5/out/obj/Vtb_hbm_slice"; then H=ot-epyc5; D=$B5; break; fi
  sleep 60
done
[ -z "${H:-}" ] && { echo "$(date) NO_BINARY after 10 h" >> $RES; exit 3; }
echo "$(date) binary $H:$D" >> $RES
one(){ N=${1%%:*}; C=${1##*:}; O=out_$N
  ssh $H "mkdir -p $D/$O && ln -sfn $D/out/obj $D/$O/obj"
  /home/ubuntu/bin/ot-run --mem 64 --threads 1 --hosts $H --dir $D -- env SRC=$D OUT=$D/$O REUSE=1 CYCLES=$C REPLAY=slice/replay/$N bash run_slice_vehicle.sh > $S/run_$N.log 2>&1
  rc=$?; r=$(ssh $H "grep -m1 -E '^SLICE_(PASS|FAIL)' $D/$O/run.log; grep -c 'SLICE_REC .*COMMIT_OK' $D/$O/run.log; grep -c 'SLICE_CHECK_FAIL' $D/$O/run.log" | tr '\n' ' ')
  echo "$N $H rc=$rc $r" >> $RES; }
export -f one; export H D S RES
xargs -P 8 -I{} bash -c 'one {}' < $S/runs.txt
echo "$(date) ALL_DONE" >> $RES
