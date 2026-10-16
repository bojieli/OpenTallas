#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
src=(tests/s81/tb_host_sd_sliced.sv rtl/dsrom_sys/s81_ingest/dsfd_host_sd_sliced.sv rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv)
for mode in 0 1 2 3 4 5; do
 args=(); if [ "$mode" -ge 1 ] && [ "$mode" -le 4 ]; then args=(-Ptb_host_sd_sliced.MUT="$mode"); fi
 if [ "$mode" = 5 ]; then args=(-Ptb_host_sd_sliced.STARVE=1); fi
 iverilog -g2012 -s tb_host_sd_sliced "${args[@]}" -o "$out/$mode.vvp" "${src[@]}" > "$out/$mode.build.log" 2>&1
 if [ "$mode" = 0 ] || [ "$mode" = 5 ]; then
  vvp -n "$out/$mode.vvp" > "$out/$mode.log"
  grep 'SD_SLICED PASS' "$out/$mode.log"
 else
  if vvp -n "$out/$mode.vvp" > "$out/$mode.log"; then echo SD_SLICED_MUTANT_ESCAPED;exit 1;fi
  grep -q 'SD_SLICED FAIL reconstruction/calendar' "$out/$mode.log"
 fi
done
sha256sum "${src[@]}" > "$out/source.sha256"
echo 'HOST_SD_SLICED_GATE PASS exact256/header/calendar+localpointer invariants,4 payload mutants,missingcredit fault without rescheduling'
