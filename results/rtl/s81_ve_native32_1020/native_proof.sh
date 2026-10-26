#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p native_proof
cd native_proof
tar -xzf ../proof_source.tar.gz
cp ../tb_s81sl_ve_native.sv .
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version >verilator_version.txt
sha256sum ../ve_native32_limit32.v ../cell_models/coupon/library_model_pdk.v ../proof_source.tar.gz >identity.sha256
/usr/bin/time -v "$V" --binary --timing -O1 --x-assign unique --x-initial unique -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GGAP=0 --top-module tb_s81sl_ve_native -Mdir obj --build-jobs 4 $(cat ../proof_files.f) ../ve_native32_limit32.v ../cell_models/coupon/library_model_pdk.v tb_s81sl_ve_native.sv >build.log 2>&1
for sd in 7 29; do
 python3 tools/s81_dv/ve_golden.py fx$sd --seed $sd >gold$sd.log
 /usr/bin/time -v obj/Vtb_s81sl_ve_native +dir=fx$sd +verilator+rand+reset+2 +verilator+seed+$sd >run$sd.log 2>&1
 grep '^PASS NATIVE' run$sd.log
done
echo NATIVE_PROOF_DONE
