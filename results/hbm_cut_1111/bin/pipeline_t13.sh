#!/bin/bash
# HBM-COMPOSE pipeline: conflicts -> ordered apply (per-step declared-key assert) -> classify -> G0 | route_supply | b4fast
# usage: pipeline.sh NAME DELTA1 DELTA2 ...   (out: $W/compose/NAME, logs $W/compose/NAME.*)
set -u
W=/srv/opentallas-scratch2/claude/hbm-cut-1111; C="python3 -I $W/bin/compose.py"; N=$1; shift
O=$W/compose/$N; L=$W/compose/$N.log; mkdir -p $W/compose; cd /
{
echo "== $N $(date -u)"; for d in "$@"; do echo "delta $(sha256sum $d)"; done
SETTLED=$W/settled.json $C conflicts "$@" > $O.conflicts.json; crc=$?; echo "conflicts rc $crc"; python3 -I -c "import json;d=json.load(open('$O.conflicts.json'));print('overlap',d['n_overlap'],'identical',d['n_identical'],'settled',d['n_settled'],'open',d['n_open'])"
[ $crc = 0 ] || { echo CONFLICT_OPEN_STOP; echo PIPE_DONE; exit 1; }
rm -rf $O; $C apply $W/compose/t12 $O $O.steps.json "$@" > $O.apply.log 2>&1; rc=$?; cut -c1-300 $O.apply.log; [ $rc = 0 ] || { echo APPLY_FAILED; rm -rf $O; echo PIPE_DONE; exit 1; }
sha256sum $O/die_plan.json $O/compiler_core_delta.json $O/core_conns.json
$C classify $W/compose/t12 $O $O.classify.json
} > $L 2>&1
[ -d $O ] || { echo PIPE_DONE >> $L; exit 1; }
( $W/bin/g0.sh $O $O.g0; python3 -I $W/bin/g0cmp.py $W/compose/t11.g0/g0_report.json/g0_report.json $O.g0/g0_report.json/g0_report.json > $O.g0cmp.txt ) &
( bash $W/bin/rs.sh $O $O.rs; python3 -I $W/bin/rscmp.py $W/compose/t11.rs/route_supply_hbm.tsv $O.rs/route_supply_hbm.tsv > $O.rscmp.tsv ) &
( B1=/srv/opentallas-scratch2/claude/cpl-hbm-b1
  for P in $W/compose/t12 $O; do python3 -I -c "import json,sys;P=json.load(open(sys.argv[1]+'/die_plan.json'));json.dump(P['partition_types'],open(sys.argv[2],'w'))" $P $O.types_$(basename $P).json; done
  for t in q_b101 q_b101_nw q_b100 q_b100__physical_v1 q_b102 q_b102__physical_v1 q_b103 q_b103__physical_v1; do
    for P in base $N; do echo "$P $(python3 -I $B1/b4fast.py $O.types_$P.json $t 2>&1 | tail -1)"; done
  done > $O.b4fast.jsonl ) &
( BR=/srv/opentallas-scratch2/claude/die-hbm-97-taps/bind/bind_p11t_taps_cyc_vK5d_c12/rtl
  [ -s $W/compose/t11.stscan.tsv ] || nice python3 -I $W/bin/stscan.py $W/compose/t12 $BR --out $W/compose/t11.stscan.tsv > $W/compose/t11.stscan_ref.log 2>&1
  nice python3 -I $W/bin/stscan.py $O $BR --out $O.stscan.tsv --detail $O.stscan.json > $O.stscan.log 2>&1 ) &
wait
{ echo "== G0"; head -1 $O.g0cmp.txt; grep '^+' $O.g0cmp.txt | cut -c1-300; echo "== route_supply WORSE"; grep '^WORSE' $O.rscmp.tsv | cut -c1-1500; echo "== stscan (type base_phantom new_phantom base_miss405 new_miss405)"; python3 -I $W/bin/stcmp.py $W/compose/t11.stscan.tsv $O.stscan.tsv; echo PIPE_DONE; } >> $L
