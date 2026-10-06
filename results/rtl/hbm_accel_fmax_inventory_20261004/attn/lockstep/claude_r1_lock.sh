#!/bin/bash
# lockstep tile_s vs tile_l; usage lock.sh <tag> <-G params...>
R=/srv/opentallas-scratch2/scratch/claude/hbm-attn
cd $R/src2
t=$1; shift
mkdir -p $R/lock
/srv/opentallas-scratch/admit.sh 16 -- $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --cc --exe --build -j 8 -O1 -CFLAGS -O1 -MAKEFLAGS OPT_SLOW=-O0 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD --top-module tb_hdc_v41x_attn_tile_s_lockstep --prefix Vtb -Mdir $R/lock/$t -GFML=6 "$@" rtl/test/tb_hdc_v41x_attn_tile_s_lockstep.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/test/hdc_v41_harness.cpp > $R/lock/$t.log 2>&1 && $R/lock/$t/Vtb > $R/lock/$t.run 2>&1
echo rc=$? >> $R/lock/$t.run
