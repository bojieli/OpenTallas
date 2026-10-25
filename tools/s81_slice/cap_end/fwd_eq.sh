#!/usr/bin/env bash
# S81/PORTFIX-DEAD D-CAPEND: one-sided node equivalence bench (repo root).  Usage: fwd_eq.sh OUTDIR [SEEDS]
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; SEEDS=${2:-"1 2 3"}; mkdir -p "$O"
S=rtl/dsrom_sys/s81_dv/slice
"$VL" --binary --top-module tb_retn_fwd_eq -Mdir "$O/obj" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
  rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv rtl/proto/ot_fp32_add_rne_pipe.sv \
  $S/ot_s81sl_cap_rt.sv $S/cap_end/ot_s81_retn_fwd.sv tools/s81_slice/cap_end/tb_retn_fwd_eq.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
for s in $SEEDS; do for pv in 10 40 90; do "$O/obj/Vtb_retn_fwd_eq" +seed=$s +pv=$pv | tee "$O/run_s${s}_pv${pv}.log" | grep RETN_FWD_EQ; done; done
