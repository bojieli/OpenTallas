#!/bin/bash
set -u
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
cd /srv/opentallas/repos/euclid-hbm-fmax-svc-order-20261005
export OT_ORFS_NUM_CORES=16 OT_PHYSICAL_WORK_ROOT=/srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-order-r4/phys_work
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
/srv/opentallas-scratch/admit.sh 16 -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_accel_dskv_wb_flat_ordered --source rtl/hbm_accel/service/ot_hbm_accel_dskv_wb_flat_ordered.sv --param ENABLE=1 --param STACK=1 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --core-input-delay-min-ns 0 --core-input-delay-max-ns 0.1666 --false-path-from rst_n --stages synth,pnr --core-utilization 30 --place-density 0.55 --hold-margin-ns 0 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --purpose signoff_target --nickname-tag svc_shadow_order_r4_euclid_0833 --keep-workdir /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-order-r4/work --output /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-order-r4/physical.json --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-order-r4/route.log 2>&1
rc=$?
echo "route_rc=$rc" > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-order-r4/exit
if compgen -G "/srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-order-r4/work/orfs/results/asap7/*/base/6_final.odb" > /dev/null; then
 python3 tools/w18/corner_sta.py --orfs-dir /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-order-r4/work/orfs --output /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-order-r4/corner_sta.json > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-order-r4/corner.log 2>&1
 echo "corner_rc=$?" >> /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-order-r4/exit
fi
