#!/bin/bash
# BUS-GEAR-2 TX smoke (iverilog): xw_v-framed ot_s81_xc_gear_tx -> real RX, random gaps, start parity SEED 1..4.
# Expect MUT 0 SMOKE PASS (every SEED), MUT 1 (two words on consecutive edges) SMOKE FAIL with flt=1.  Run from repo root.
O=${1:-/tmp/tx_smoke.vvp}
iverilog -g2012 -s tb -o $O results/arch/bus_gear_1112/bench/tb_s81_xc_gear_tx_smoke.sv rtl/dsrom_sys/s81_dv/xgear/ot_s81_xgear_die.sv \
  rtl/dsrom_sys/s81_dv/xgear/ot_s81_xlane_gear.sv rtl/common/ot_bus_gear.sv rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv || exit 2
bad=0
for c in "0 1 PASS" "0 2 PASS" "0 3 PASS" "0 4 PASS" "1 1 FAIL" "1 2 FAIL"; do set -- $c
  r=$(vvp -n $O +MUT=$1 +SEED=$2 | grep SMOKE); echo "$r (expect $3)"; case "$r" in *"SMOKE $3"*) ;; *) bad=1;; esac
done
[ $bad = 0 ] && echo "TX SMOKE PASS" || { echo "TX SMOKE FAIL"; exit 1; }
