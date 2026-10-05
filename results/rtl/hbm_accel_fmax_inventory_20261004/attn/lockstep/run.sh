#!/bin/bash
cd /srv/opentallas-scratch/claude/hbm-fmax-attn/src
t=$1; shift
/srv/opentallas-scratch/admit.sh 30 -- /usr/bin/time -v ~/.local/opentallas-tools/verilator-5.050/bin/verilator --cc --exe --build -j 8 -O1 -CFLAGS -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD --top-module tb_hdc_v41x_attn_tile_s_lockstep --prefix Vtb -Mdir ../lock/$t "$@" -GFPL=7 -GFML=6 rtl/test/tb_hdc_v41x_attn_tile_s_lockstep.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/test/hdc_v41_harness.cpp > ../lock/$t.log 2>&1 && ../lock/$t/Vtb > ../lock/$t.run 2>&1
echo rc=$? >> ../lock/$t.run
