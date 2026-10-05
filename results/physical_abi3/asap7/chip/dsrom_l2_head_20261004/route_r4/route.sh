#!/bin/bash
# usage: route.sh NV XS OUTDIR  -- ot_v41_rom_elem_nv_w10 (FAST PP BP=2 MTP NB=2 EARLY) routed at 833 ps, SS setup / SS+FF hold
NV=$1; XS=$2; O=$3
cd $SRCDIR
mkdir -p $O
SRC=""
for s in rtl/v41rom/ot_v41_rom_elem_nv_w10.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bmul2.sv rtl/v41rom/ot_v41_bterm2_w10.sv rtl/v41rom/ot_v41_chain2.sv rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v; do SRC="$SRC --source $s"; done
~/bin/admit.sh 20 -- python3 tools/run_abi3_physical.py --view asap7 --top ot_v41_rom_elem_nv_w10 $SRC \
  --param FAST=1 --param PP=1 --param BP=2 --param MTP=1 --param NB=2 --param EARLY=1 --param NCH=24 --param NV=$NV --param XS=$XS \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --orfs-var ADDER_MAP_FILE= --max-transition-ns --max-fanout 32 \
  --stages pnr --false-path-io --core-utilization ${UTIL:-40} --macro-place-halo 3 3 --hold-margin-ns 0.01 \
  --macro-view ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8 \
  --nickname-tag l2nv${NV}xs${XS} --keep-workdir $O/work --output $O/physical.json > $O/route.log 2>&1
echo $? > $O/route.exit
