#!/bin/bash
set -euo pipefail
export TMPDIR=/srv/opentallas/jobs-overflow/hubble-wg-gearbox-r2/tmp NUM_CORES=4 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
mkdir -p "$TMPDIR"
O=/srv/opentallas/jobs-overflow/hubble-wg-gearbox-r2
S=/srv/opentallas/jobs-overflow/hubble-w2-chunks-r2
cd "$O"
cp "$S"/{ot_hbm_accel_wg_gearbox.sv,tb_hbm_accel_wg_gearbox.sv} .
sha256sum *.sv > source.sha256
awk "/MemAvailable/{print}" /proc/meminfo > headroom.txt
df -B1 "$O" >>headroom.txt
verilator --binary --timing -O2 -Wno-fatal -j 4 --top-module tb_hbm_accel_wg_gearbox --Mdir "$O/obj" *.sv > compile.log 2>&1
P=/srv/opentallas/jobs-overflow/hubble-expert-interleave-r1/native/L20_stack0
for k in 0 1 2 3 4 5; do "$O/obj/Vtb_hbm_accel_wg_gearbox" +DIR="$P" +slot="$k" > "slot${k}.log" 2>&1;grep -q GEARBOX_ACTUAL_BYTE_PASS "slot${k}.log"; done
if "$O/obj/Vtb_hbm_accel_wg_gearbox" +DIR="$P" +slot=0 +mut=1 > corrupted_FAIL.log 2>&1; then echo FAILED_NEGATIVE;exit 1;fi
grep -q "actual source byte mismatch" corrupted_FAIL.log
sha256sum -c source.sha256 > postcheck.txt
printf PASS_MINIMUM_GEARBOX_ACTUAL_L20_BYTES > terminal.txt
