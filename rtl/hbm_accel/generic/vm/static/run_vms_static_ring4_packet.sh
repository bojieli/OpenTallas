#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
out="${1:-/tmp/hbm-static-ring4-packet-run}"
stop_root="${STATIC_STOP_ROOT:-.}"
macro="${SRAM_MODEL:-../../../../../physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v}"
if [ -f ot_sram_1r1w_1024x256_m2_r2c2.v ]; then macro=ot_sram_1r1w_1024x256_m2_r2c2.v; fi
mkdir -p "$out"
for mut in 0 1; do
/usr/bin/time -v -o "$out/compile-$mut.time" iverilog -g2012 -s tb_vms_static_ring4_packet -Ptb_vms_static_ring4_packet.MUT="$mut" -o "$out/ring-$mut.vvp" ot_vms_bank_static.sv "$stop_root/ot_vms_rstop_static.sv" "$stop_root/ot_vms_rcl_static.sv" "$stop_root/ot_vms_hub_static.sv" "$macro" tb_vms_static_ring4_packet.sv > "$out/compile-$mut.log" 2>&1
set +e
/usr/bin/time -v -o "$out/sim-$mut.time" vvp "$out/ring-$mut.vvp" > "$out/sim-$mut.log" 2>&1
rc=$?
set -e
cat "$out/sim-$mut.log"
if [ "$mut" -eq 0 ]; then test "$rc" -eq 0; else test "$rc" -ne 0; fi
done
printf 'PASS ring4 real SRAM positive + wrong replay return-port mutant gate\n'
