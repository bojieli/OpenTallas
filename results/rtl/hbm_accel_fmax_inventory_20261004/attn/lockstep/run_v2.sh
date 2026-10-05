#!/bin/bash
cd ~/hbm-fmax-attn/src
t=$1; shift
~/bin/admit.sh 16 -- /usr/bin/time -v ~/.local/opentallas-tools/verilator-5.050/bin/verilator --cc --exe --build -j 6 -O1 -CFLAGS -O1 -MAKEFLAGS OPT_SLOW=-O0 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD --top-module tb_hdc_v41x_attn_tile_s_lockstep --prefix Vtb -Mdir ../lock2/$t "$@" -GFML=6 rtl/test/tb_hdc_v41x_attn_tile_s_lockstep.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/test/hdc_v41_harness.cpp > ../lock2/$t.log 2>&1 && ../lock2/$t/Vtb > ../lock2/$t.run 2>&1
echo rc=$? >> ../lock2/$t.run
