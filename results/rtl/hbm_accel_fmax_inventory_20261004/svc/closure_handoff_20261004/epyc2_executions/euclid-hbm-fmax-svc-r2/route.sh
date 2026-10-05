#!/bin/bash
set -u
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
cd /srv/opentallas/repos/euclid-hbm-fmax-svc-20261004
export OT_ORFS_NUM_CORES=16 OT_PHYSICAL_WORK_ROOT=/srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r2/phys_work
/srv/opentallas-scratch/admit.sh 16 -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_accel_dskv_wb --source rtl/hbm_accel/service/ot_hbm_accel_dskv_wb.sv --param ENABLE=1 --param STACK=1 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --core-input-delay-min-ns 0 --core-input-delay-max-ns 0.1666 --false-path-from rst_n --stages synth,pnr --core-utilization 30 --place-density 0.55 --hold-margin-ns 0 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --purpose signoff_target --nickname-tag svc_dskvwb_r1d_euclid_0833 --keep-workdir /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r2/work --output /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r2/physical.json > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r2/route.log 2>&1
rc=$?
echo "rc=$rc" > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r2/exit
if [ "$rc" -eq 0 ]; then
 python3 tools/w18/corner_sta.py --orfs-dir /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r2/work/orfs --output /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r2/corner_sta.json > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r2/corner.log 2>&1
 echo "corner_rc=$?" >> /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r2/exit
fi
