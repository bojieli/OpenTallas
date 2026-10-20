#!/bin/bash
set -eu
export PATH=/opt/verilator-5.050/bin:$PATH
for c in positive addr_mut tag_mut;do
 mkdir -p "$c/obj"
 defs='-DOT_BF_FOREP -DOT_BF_FOREP32 -DOT_BF_HELD_SRAM -DOT_BF_ACC_SRAM -DOT_BF_TAG_RING'
 if [ "$c" = addr_mut ];then defs="$defs -DOT_BF_ACC_SRAM_MUT_ADDR";fi
 if [ "$c" = tag_mut ];then defs="$defs -DOT_BF_TAG_RING_MUT_AGE";fi
 verilator --binary --timing -Wno-fatal -j 4 --top-module tb --Mdir "$c/obj" $defs tb.sv old_chain.sv rtl/v41rom/{ot_v41_chain4_rp,ot_v41_segtree5_rp,ot_v41_fadd_rp,ot_v41_fadd2_rp,ot_v41_fadd2,ot_v41_fadd,ot_v41_kreg,ot_v41_rst_copy}.sv rtl/hdc/ot_hdc_delay.sv rtl/common/ot_prefix.sv > "$c.build.log" 2>&1
 set +e
 "$c/obj/Vtb" > "$c.log" 2>&1;rc=$?
 set -e
 if [ "$c" = positive ];then test "$rc" = 0;grep 'ACC_SRAM PASS' "$c.log";else test "$rc" -ne 0;grep 'ACC_DIFF' "$c.log";fi
done
