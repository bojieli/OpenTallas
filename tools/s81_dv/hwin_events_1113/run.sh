#!/bin/bash
set -eu
cd "${1:?staged packet directory}"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
ulimit -c 0
verilator --binary --timing -Wno-fatal -j 2 -CFLAGS -O0 --top-module tb_hwin_events --Mdir obj ot_rst_relay.sv dsdv_mu_hwin.sv tb_hwin_events.sv > build.log 2>&1
./obj/Vtb_hwin_events > run.log 2>&1
./obj/Vtb_hwin_events +STALE_RX=1 > stale_rx.log 2>&1
grep -q 'HWIN_EVENTS_PASS' run.log
grep -q 'HWIN_STALE_RX_CAUGHT' stale_rx.log
for delay in 1 299; do
  ./obj/Vtb_hwin_events +RX_DELAY=$delay > rx_$delay.log 2>&1
  grep -q HWIN_EVENTS_PASS rx_$delay.log
done
for delay in 0 300; do
  ./obj/Vtb_hwin_events +RX_DELAY=$delay > rx_$delay.log 2>&1
  grep -q HWIN_STALE_RX_CAUGHT rx_$delay.log
done
