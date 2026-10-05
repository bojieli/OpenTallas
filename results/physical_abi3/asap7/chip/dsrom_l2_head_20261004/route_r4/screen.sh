#!/bin/bash
# usage: screen.sh NV WORKDIR
NV=$1; W=$2
cd $SRCDIR
SRC=""
for s in rtl/v41rom/ot_v41_rom_elem_nv_w10.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bmul2.sv rtl/v41rom/ot_v41_bterm2_w10.sv rtl/v41rom/ot_v41_chain2.sv rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v; do SRC="$SRC --source $s"; done
~/bin/admit.sh 10 -- python3 tools/gpu_ss_prelayout.py --top ot_v41_rom_elem_nv_w10 $SRC --period-ps 833 --work $W \
  --param FAST=1 --param PP=1 --param BP=2 --param MTP=1 --param NB=2 --param EARLY=1 --param NCH=24 --param NV=$NV --param XS=${XS:-8} > $W.log 2>&1
python3 tools/dsrom_l2_head_sta_macro.py $W ot_v41_rom_elem_nv_w10 >> $W.log 2>&1
