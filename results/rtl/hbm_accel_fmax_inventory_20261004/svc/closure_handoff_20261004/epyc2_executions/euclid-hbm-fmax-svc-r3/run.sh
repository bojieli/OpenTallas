#!/bin/bash
set -u
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
cd /srv/opentallas/repos/euclid-hbm-fmax-svc-flat-20261004
/srv/opentallas-scratch/admit.sh 8 -- verilator --binary --timing -Wno-fatal --top-module tb_dskv_wb_lockstep -GSTACK=1 -GRP=2 -GPOSMODE=0 --Mdir /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/obj -j 16 results/rtl/hbm_accel_fmax_inventory_20261004/svc/closure_handoff_20261004/tb_dskv_wb_flat_lockstep.sv results/rtl/hbm_accel_fmax_inventory_20261004/svc/closure_handoff_20261004/ot_hbm_accel_dskv_wb_r0_ref.sv rtl/hbm_accel/service/ot_hbm_accel_dskv_wb_flat.sv > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/compile.log 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then echo "phase=lockstep_compile rc=$rc" > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/exit; exit "$rc"; fi
for seed in 1 2; do
 /srv/opentallas-scratch/admit.sh 2 -- /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/obj/Vtb_dskv_wb_lockstep +SEED=$seed +CYC=500000 > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/lockstep_seed$seed.log 2>&1
 rc=$?
 if [ "$rc" -ne 0 ] || ! grep -q 'cycles=500000 mismatches=0.*verdict=PASS' /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/lockstep_seed$seed.log; then echo "phase=exactness seed=$seed rc=$rc verdict=FAIL" > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/exit; exit 1; fi
done
echo "lockstep=PASS" > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/exactness.exit
export OT_ORFS_NUM_CORES=16 OT_PHYSICAL_WORK_ROOT=/srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/phys_work
/srv/opentallas-scratch/admit.sh 16 -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_accel_dskv_wb_flat --source rtl/hbm_accel/service/ot_hbm_accel_dskv_wb_flat.sv --param ENABLE=1 --param STACK=1 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --core-input-delay-min-ns 0 --core-input-delay-max-ns 0.1666 --false-path-from rst_n --stages synth,pnr --core-utilization 30 --place-density 0.55 --hold-margin-ns 0 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --purpose signoff_target --nickname-tag svc_dskvwb_flat_r3_euclid_0833 --keep-workdir /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/work --output /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/physical.json > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/route.log 2>&1
rc=$?
echo "phase=route rc=$rc" > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/exit
if [ "$rc" -eq 0 ]; then
 python3 tools/w18/corner_sta.py --orfs-dir /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/work/orfs --output /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/corner_sta.json > /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/corner.log 2>&1
 echo "corner_rc=$?" >> /srv/opentallas-scratch/jobs/euclid-hbm-fmax-svc-r3/exit
fi
