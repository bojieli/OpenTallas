#!/bin/bash
set -eu
cd src
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
verilator --lint-only -Wall -Wno-fatal --top-module ot_s81sl_lep_mu_h -GRX_SRAM=1 rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_wreg.sv rtl/lib/ot_rst_relay.sv rtl/lib/ot_sram_showahead_1r1w.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v > ../lint_raw.log 2>&1
cat ../lint_raw.log
