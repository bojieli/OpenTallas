#!/bin/bash
set -eu
python3 native_su_calendar.py readback_expected.mem release18_cal --first-serial 2675 --bridge-serial 2675 --bridge-stream 3567 --host-launch 3500 --rows 160 --request-lane-edges 4
cp release18_cal/calendar.mem calendar.mem
verilator --binary --timing -Wno-fatal --top-module tb --Mdir obj_release18 -j 6 release18_tb.sv ckgen.sv pgp.sv bridge.sv release.sv tap_exact.sv vmb.sv hfd_hgi_vm_calendar_f20.sv ot_hbm_host_cfg_leaf_sw.sv ot_hbm_su_static_vm_ports.sv > release18_build.log 2>&1
W=$(wc -l < readback_image/config.mem)
obj_release18/Vtb +CFG=readback_image/config.mem +GOLD=readback_expected.mem +N=62 +W=$W > release18.log 2>&1
for m in 1 2 3; do if obj_release18/Vtb +CFG=readback_image/config.mem +GOLD=readback_expected.mem +N=62 +W=$W +MUT=$m > release18_mutant${m}.log 2>&1; then echo "UNEXPECTED MUTANT PASS $m"; exit 1; fi; grep -Eq 'PRODUCER FAIL|NATIVE_DATA FAIL' release18_mutant${m}.log; done
sha256sum *.sv native_su_calendar.py readback_expected.mem readback_image/config.mem calendar.mem > release18_source.sha256

mkdir -p wrong_request_lane
python3 native_su_calendar.py readback_expected.mem wrong_request_lane --first-serial 2675 --bridge-serial 2675 --bridge-stream 3567 --host-launch 3500 --rows 160 --request-lane-edges 3
if (cd wrong_request_lane; ../obj_release18/Vtb +CFG=../readback_image/config.mem +GOLD=../readback_expected.mem +N=62 +W=$W > ../release18_wrong_lane.log 2>&1); then echo 'UNEXPECTED WRONG LANE PASS'; exit 1; fi
grep -Eq 'PRODUCER FAIL|NATIVE_DATA FAIL' release18_wrong_lane.log
