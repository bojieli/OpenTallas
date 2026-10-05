#!/bin/bash
set -u
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
cd /srv/opentallas/repos/euclid-svc-fanout-20261005
export OT_ORFS_NUM_CORES=16 OT_PHYSICAL_WORK_ROOT=/srv/opentallas-scratch/jobs/euclid-svc-b-cmd-u45-r1/phys_work
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
/srv/opentallas-scratch/admit.sh 16 -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_accel_stream_pc_wb_command_match --source rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb_command_match.sv --param ENABLE=1 --param REF_MODE=1 --param PC=0 --param CRED=64 --param WB_EN=1 --param WA_LATE=1 --param DIGEST_CUT=1 --param CMD_MATCH_CUT=1 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0 --false-path-from rst_n --stages synth,pnr --core-utilization 45 --place-density 0.6 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --purpose signoff_target --nickname-tag euclid_svc_b_cmd_u45_r1_0833 --keep-workdir /srv/opentallas-scratch/jobs/euclid-svc-b-cmd-u45-r1/work --output /srv/opentallas-scratch/jobs/euclid-svc-b-cmd-u45-r1/physical.json --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited > /srv/opentallas-scratch/jobs/euclid-svc-b-cmd-u45-r1/route.log 2>&1
rc=$?
echo "route_rc=$rc" > /srv/opentallas-scratch/jobs/euclid-svc-b-cmd-u45-r1/exit
if compgen -G "/srv/opentallas-scratch/jobs/euclid-svc-b-cmd-u45-r1/work/orfs/results/asap7/*/base/6_final.odb" > /dev/null; then
 python3 tools/w18/corner_sta.py --orfs-dir /srv/opentallas-scratch/jobs/euclid-svc-b-cmd-u45-r1/work/orfs --output /srv/opentallas-scratch/jobs/euclid-svc-b-cmd-u45-r1/corner_sta.json > /srv/opentallas-scratch/jobs/euclid-svc-b-cmd-u45-r1/corner.log 2>&1
 echo "corner_rc=$?" >> /srv/opentallas-scratch/jobs/euclid-svc-b-cmd-u45-r1/exit
fi
