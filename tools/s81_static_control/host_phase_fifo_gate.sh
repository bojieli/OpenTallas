#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
for kind in 0 1; do
 for ratio in '6 6' '6 8' '8 6'; do
  read -r wp rp <<< "$ratio"
  name=a${kind}_w${wp}_r${rp}
  iverilog -g2012 -DOT_S81_HOST_PHASESAFE -s tb_host_phase_fifo -Ptb_host_phase_fifo.ASYNC="$kind" -Ptb_host_phase_fifo.WP="$wp" -Ptb_host_phase_fifo.RP="$rp" -o "$out/$name.vvp" tests/s81/tb_host_phase_fifo.sv rtl/link/ot_link_afifo.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv
  vvp -n "$out/$name.vvp" > "$out/$name.log"
  cat "$out/$name.log"
 done
done
iverilog -g2012 -DOT_S81_HOST_PHASESAFE -s tb_host_phase_fifo -Ptb_host_phase_fifo.MUT=1 -o "$out/mut.vvp" tests/s81/tb_host_phase_fifo.sv rtl/link/ot_link_afifo.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv
if vvp -n "$out/mut.vvp" > "$out/mut.log"; then echo 'PHASE_FIFO MUTANT_ESCAPED';exit 1;fi
grep -q 'PHASE_FIFO FAIL order' "$out/mut.log"
echo 'HOST_PHASE_FIFO_GATE PASS six positive ratios and corrupt-head mutant'
