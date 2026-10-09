#!/bin/bash
# Closure-loop route / calibrate wrapper for the PQ q-element (2026-10-06, SAFE QS = 3, owner decision 23:00).
#   cl_route_qs.sh <label> <job root> [--pnr-stop-after cts]      (cwd = the job's source snapshot)
# Recipe = route Z29c (QM = 5, FH 192.24, PD 0.65, ICG-enable adjacency hook, Z18d CTS + NDR + balance, SM 20, HM from
# the environment, default 25 ps) with the SDC period at the 0.833 sign-off and the 0.730 over-constraint carried by the
# setup uncertainty (UNC 0.163, INMAX 0.624; see Z23_launch.sh).  A full run also signs off: tools/w18/corner_sta.py with
# the sign-off post-SDC that cl_signoff_sdc.sh wrote from the calibration -> <job>/corner_sta.json; <job>/exit holds
# rc= / corner_rc=.
L=$1; JR=$2; shift 2
STOP=finish; [ "${1:-}" = "--pnr-stop-after" ] && STOP=$2
J=$JR/jobs/$L
# cont-takeover 2026-10-09: the persistent launcher refuses an existing workdir, so a loop retry (crash retry or the
# HOLD-STOP resume with OT_HOLD_STOP) crashed at once ("fresh workdir and receipt required"); keep the earlier attempt
# beside it and start fresh (the retry carries OT_HOLD_STOP, so its CTS hold repair stops at the measured stall point).
if [ -e $J/receipt.json ]; then n=1; while [ -e $J.prev$n ]; do n=$((n+1)); done; mv $J $J.prev$n; fi
mkdir -p $J
WT=$PWD RUN=$L JROOT=$JR STOP=$STOP QX=10 PQ=1 QW=0 QM=${QM:-5} QS=${QS:-3} HM=${HM:-0.025} SM=20 PER=0.833 UNC=0.163 INMAX=0.624 \
  FH=${FH:-192.24} PD=${PD:-0.65} PDH=physical/abi3/dsrom_q_icg_en_adjacent.tcl OT_ORFS_NUM_CORES=${THREADS:-16} \
  CTSA="-sink_clustering_enable -repair_clock_nets -sink_clustering_size 30 -sink_clustering_max_diameter 50 -distance_between_buffers 60 -apply_ndr full -balance_levels" \
  bash tools/dsrom_qelem_cl/launch.sh
rc=$?
echo "rc=$rc" > $J/exit
if [ "$STOP" = finish ] && [ $rc = 0 ]; then
  SO=physical/abi3/gen/dsrom_q_cl_signoff.sdc
  [ -f $SO ] || bash tools/dsrom_qelem_cl/cl_signoff_sdc.sh
  H1_ARGS=()
  if [ "${OT_NATIVE_Q_H1_INPUT:-0}" = 1 ]; then
    H1_ARGS=(--post-sdc .ot_mm/io_ref_routed.sdc --post-sdc tools/dsrom_qelem_cl/native_q_h1_input.sdc)
  fi
  python3 tools/w18/corner_sta.py --orfs-dir $J/work/orfs --post-sdc $SO "${H1_ARGS[@]}" \
    --macro physical/asap7_memory_macros/ot_rom_4096x274_m8 --output $J/corner_sta.json > $J/corner.log 2>&1
  echo "corner_rc=$?" >> $J/exit
fi
exit $rc
