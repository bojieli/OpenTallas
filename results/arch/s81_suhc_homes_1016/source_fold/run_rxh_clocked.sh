#!/bin/bash
set -euo pipefail
verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_s81_su_rxh_clocked_eq -Mdir obj -j 8 -GNJOB=48 rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxt.sv rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv rtl/dsrom_sys/s81_suhc/ot_s81_su_rx.sv rtl/hdc/v41x/ot_hdc_v41x_spshort.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv ot_s81_su_rxh_clocked_candidate.sv tb_s81_su_rxh_clocked_eq.sv > build.log 2>&1
for seed in 1 2; do
 obj/Vtb_s81_su_rxh_clocked_eq +SEED=$seed > positive_s$seed.log 2>&1
 grep -q '^RXH_EQ PASS' positive_s$seed.log
done
for root in $(seq 0 37); do
 set +e
 obj/Vtb_s81_su_rxh_clocked_eq +SEED=1 +STOP_ROOT=$root > clock_stop_$root.log 2>&1
 rc=$?
 set -e
 if [ "$rc" -eq 0 ] && grep -q '^RXH_EQ PASS' clock_stop_$root.log; then
  echo "CLOCK_STOP_UNOBSERVED $root";exit 1
 fi
 grep -q '^RXH_EQ FAIL' clock_stop_$root.log
 echo "CLOCK_STOP_REJECTED $root"
done
echo 'CLOCKED_RXH_GATE PASS'
