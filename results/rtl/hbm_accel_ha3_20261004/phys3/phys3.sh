#!/bin/bash
# r2: dies >= 525 um (21,672 IO pins need a 2,081 um perimeter; r1 at 360/420 would fail PPL-0024). HA3 EPI=0 (cut-through port only; the fused epilogue R3b is rejected): in-context route, SS primary (WC), hold WC+BC,
# 0.833 ns, 60/25 ps, hold margin 10 ps.  ORFS synthesis only (no host pre-layout synth: it folds pre-repair sta).
E=/srv/opentallas-scratch/claude/ha3/phys3; W=$E/src; O=$E/out; J=$E/jobs
cd $W
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=14400
SRC=$(cat /srv/opentallas-scratch/claude/ha3/phys3/jobs/deps.txt)
COMMON="--view asap7 --top ot_hbm_accel_coll_port_ctx $SRC --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --corner TT --orfs-corner WC --hold-corners WC,BC --max-transition-ns --max-fanout 32 --slew-margin-percent 30 --false-path-io --orfs-var ADDER_MAP_FILE= --keep-heavy-artifacts --hold-margin-ns 0.01"
run() { # ha3 epi tag die
  echo "$(date -Is) START $3" >> $J/MANIFEST
  /srv/opentallas-scratch/admit.sh 32 -- python3 tools/run_abi3_physical.py $COMMON --param HA3=$1 --param EPI=$2 --param FLAT=7 --stages pnr --die-area 0 0 $4 $4 --core-area 2.16 2.16 $(($4-2)).84 $(($4-2)).84 --nickname-tag ha3p3_$3 --keep-workdir $O/work_$3 --output $O/$3.json --force > $J/$3.log 2>&1
  echo $? > $J/$3.exit; echo "$(date -Is) END $3 exit=$(cat $J/$3.exit)" >> $J/MANIFEST
}
run 1 0 route_e0 540 &
run 1 0 route_e0w 600 &
run 0 1 route_h0 540 &
wait
echo "$(date -Is) TERMINAL" >> $J/MANIFEST
