#!/bin/bash
cd /srv/opentallas-scratch/claude/s81-l20rd3-1020/src3
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$VL --lint-only -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-PINCONNECTEMPTY -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-TIMESCALEMOD --top-module dsdv_idx_rg2 \
  rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv \
  rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv \
  rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv 2>&1 | grep -E '%(Error|Warning)' | grep 'idx_rg2' | head -40
echo LINT_DONE
