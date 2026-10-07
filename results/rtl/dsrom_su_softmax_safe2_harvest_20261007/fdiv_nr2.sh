#!/bin/bash
# divider equivalence: $1 = src dir, $2 = tag, NR 1, 10M pairs over 4 seeds
B=/srv/opentallas-scratch2/scratch/claude/dsrom-su-softmax-r5
cd $B/src_safe
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
O=$B/work/obj_fdiv_nr2_$2
$VL --binary -O2 -Wno-fatal -Wno-WIDTH --top-module tb_dsrom_su_fdiv_f12_eq -GNR=2 -Mdir $O rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/test/sim_hdc_prefix_beh.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv rtl/test/tb_dsrom_su_fdiv_f12_eq.sv -j 8 > $B/work/fdiv_build_nr2_$2.log 2>&1 || { echo "EXIT build" > $B/work/fdiv_nr2_$2.log; exit 2; }
for s in 1 2 3 4; do $O/Vtb_dsrom_su_fdiv_f12_eq +N=2500000 +SEED=$s; done > $B/work/fdiv_nr2_$2.log 2>&1
echo "EXIT $?" >> $B/work/fdiv_nr2_$2.log
