#!/bin/bash
set -u
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
cd /srv/opentallas/repos/euclid-svc-aq-head-ready-973696-20261005
export OT_ORFS_NUM_CORES=16 OT_PHYSICAL_WORK_ROOT=/srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-route-r1/phys_work
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
/srv/opentallas-scratch/admit.sh 16 -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_r14_stream_stack_aq_head_ready_cut --source rtl/hbm_accel/svc/aq_head_ready_cut/ot_hbm_r14_stream_pc_aq_head_ready_cut.sv --source rtl/hbm_accel/svc/aq_head_ready_cut/ot_hbm_r14_stream_stack_aq_head_ready_cut.sv --param ENABLE=1 --param REF_MODE=1 --param NCH=1 --param WR_EN=1 --param WQ=4 --param PULLIN=16 --param AQ_RD=1 --param AQ_HOLD_LOOKAHEAD=1 --param AQ_HEAD_READY_LOOKAHEAD=1 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0 --false-path-from rst_n --stages synth,pnr --core-utilization 40 --place-density 0.6 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --purpose signoff_target --nickname-tag svc_aq_head_ready_r1_euclid_0833 --keep-workdir /srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-route-r1/work --output /srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-route-r1/physical.json --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited > /srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-route-r1/route.log 2>&1
rc=$?
echo "route_rc=$rc" > /srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-route-r1/exit
if compgen -G "/srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-route-r1/work/orfs/results/asap7/*/base/6_final.odb" > /dev/null; then
 python3 tools/w18/corner_sta.py --orfs-dir /srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-route-r1/work/orfs --output /srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-route-r1/corner_sta.json > /srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-route-r1/corner.log 2>&1
 echo "corner_rc=$?" >> /srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-route-r1/exit
fi
