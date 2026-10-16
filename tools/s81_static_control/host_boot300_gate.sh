#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
mapfile -t src < <(python3 tools/die_port_bind.py none --closure dsfd_host_c)
for mut in 0 5;do
  iverilog -g2012 -DDSFD_HOST_C_STATIC -DDSFD_HOST_PQ_BOOT -DOT_S81_HOST_PHASESAFE -DOT_S81_HOST_BOOT300 -s tb_host_boot300 -Ptb_host_boot300.MUT="$mut" -o "$out/m${mut}.vvp" "${src[@]}" tests/s81/tb_host_boot300.sv > "$out/build${mut}.log" 2>&1
 done
for phase in 0 1 2 3 4 5 6 7;do
 vvp -n "$out/m0.vvp" +serial_phase="$phase" > "$out/p${phase}.log"
 grep 'BOOT300 PASS' "$out/p${phase}.log"
done
if vvp -n "$out/m5.vvp" > "$out/kind_mut.log";then echo BOOT300_MUTANT_ESCAPED;exit 1;fi
grep -q 'BOOT300 FAIL payload/kind' "$out/kind_mut.log"
vvp -n "$out/m0.vvp" +stop_boot=1 > "$out/stop.log"
grep -q 'BOOT300 FAIL_EXPECTED detected stop=1' "$out/stop.log"
vvp -n "$out/m0.vvp" +overload=1 > "$out/full.log"
grep -q 'BOOT300 FAIL_EXPECTED detected stop=0 overload=1' "$out/full.log"
echo 'HOST_BOOT300_GATE PASS 8 rational phases payload/identity/length + typed-kind mutant + missing-clock/capacity faults'
