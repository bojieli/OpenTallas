#!/bin/bash
# lockstep hfd_attn_tile_b vs the quad parent: lockb.sh <tag> <-G params...>
R=/srv/opentallas-scratch2/scratch/claude/hbm-attn
cd $R/src_bk
t=$1; shift
mkdir -p $R/lockb
/srv/opentallas-scratch/admit.sh 24 -- $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --cc --exe --build -j 16 -O1 -CFLAGS -O1 -MAKEFLAGS OPT_SLOW=-O0 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-PINMISSING --top-module tb_hfd_attn_tile_b --prefix Vtb -Mdir $R/lockb/$t "$@" rtl/test/tb_hfd_attn_tile_b.sv rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv rtl/hdc/v41x/ot_hdc_v41x_attn_bank.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m6h1r.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m8_phys.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/test/hdc_v41_harness.cpp > $R/lockb/$t.log 2>&1 && $R/lockb/$t/Vtb > $R/lockb/$t.run 2>&1
echo rc=$? >> $R/lockb/$t.run
