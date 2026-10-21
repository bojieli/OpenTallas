#!/bin/bash
# run from the bench root; Verilator 5.050 (ot-heavy PATH)
cd "$(dirname "$0")"
r=0
run(){ n=$1; shift; "$@" > logs/$n.out 2>&1; echo "$n rc=$? $(grep -E 'PASS|FAIL' logs/$n.out | tail -1)"; }
mkdir -p logs
run pos_obr1_safe1 bash tools/hbm_static/su_cxport_split_vl_run.sh b/pos 2 0 0 0 1 1 &
run q0_obr1_safe1 bash tools/hbm_static/su_cxport_split_vl_run.sh b/q0 0 1 0 0 1 1 &
run mut1_obr1_safe1 bash tools/hbm_static/su_cxport_split_vl_run.sh b/mut1 2 0 1 1 1 1 &
run mut4_obr1_safe1 bash tools/hbm_static/su_cxport_split_vl_run.sh b/mut4 2 0 4 1 1 1 &
run pos_obr0_safe0 bash tools/hbm_static/su_cxport_split_vl_run.sh b/pos00 2 0 0 0 0 0 &
run safe_sd0 bash tools/hbm_static/cxijq_safe_one.sh b/s0 0 0 &
run safe_mut6 bash tools/hbm_static/cxijq_safe_one.sh b/s6 0 6 &
wait
