#!/bin/bash
# s81-ctl-1011 sel / col engine endpoint gate (ADAPTER_CONTRACT_1011 engines 5 / 6): the exact selector / collector
# benches with +define+TB_CTRL (endpoint tiles dsfd_dw_ep_s / dsfd_dw_ep_c on the slab's vd, one descriptor a segment /
# job; done tags, order, no early done, no fault).  Mutants must FAIL: wrong descriptor tag (TB_MUT_WRONGTAG), wrong done
# tag (endpoint MUT 2), dropped done (MUT 4).  Run from the repo root on a fleet host (ot-heavy):
#   run_selcol_ctrl_gate.sh <out dir>       -> <out>/verdict.log, exit 0 iff SELCOL_CTRL_GATE PASS
set -u
O=$1; mkdir -p $O
CT="rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv rtl/dsrom_sys/s81_ctrl/ot_s81_done_word.sv rtl/dsrom_sys/s81_ctrl/dsfd_dw_ep.sv"
SEL="rtl/common/ot_fwd_link_stage.sv rtl/hdc/ot_hdc_prefix.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_pp.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv rtl/dsrom_sys/s81_ph/dsfd_bk_selector.sv rtl/dsrom_sys/s81_ph/test/tb_s81ph_sel.sv"
COL="rtl/common/ot_fwd_link_stage.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v rtl/link/ot_fifo_sram_fwft.sv rtl/dsrom_sys/s81_ph/ot_s81ph_col.sv rtl/dsrom_sys/s81_ph/ot_s81ph_col_tile.sv rtl/dsrom_sys/s81_ph/dsfd_bk_collector.sv rtl/dsrom_sys/s81_ph/test/tb_s81ph_col.sv"
run() {   # run <label> <tb> <srcs> <plusargs> <pass regex> [defines...]
  l=$1; tb=$2; s=$3; pa=$4; re=$5; shift 5
  mkdir -p $O/$l
  verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module $tb "$@" -Mdir $O/$l/obj $CT $s > $O/$l/build.log 2>&1 \
    || { echo BUILD_FAIL > $O/$l/rc; return 2; }
  $O/$l/obj/V$tb $pa > $O/$l/run.log 2>&1
  if grep -q "$re" $O/$l/run.log && ! grep -q "^FAIL\|^ERR ctrl" $O/$l/run.log; then echo PASS > $O/$l/rc; return 0; fi
  echo FAIL > $O/$l/rc; return 1
}
if [ "${2:-}" = one ]; then   # run_selcol_ctrl_gate.sh <out> one <sel|col> [defines]: one case, exit 0 iff PASS
  k=$3; shift 3
  if [ $k = sel ]; then run one_sel tb_s81ph_sel "$SEL" "" "^RESULT PASS" -DTB_CTRL "$@"; r=$?; else run one_col tb_s81ph_col "$COL" "+jobs=40" "^RESULT PASS" -DTB_CTRL "$@"; r=$?; fi
  echo "SELCOL_ONE $k $* rc=$r ($(cat $O/one_$k/rc))"; exit $r
fi
# SEQ=1: one build at a time (fits a small ot-heavy slot, < 32 GB)
P_='&'; [ "${SEQ:-0}" = 1 ] && P_=''
if [ -z "$P_" ]; then run sel_base tb_s81ph_sel "$SEL" "" "^RESULT PASS" -DTB_CTRL; echo $? > $O/.a0; else ( run sel_base tb_s81ph_sel "$SEL" "" "^RESULT PASS" -DTB_CTRL; echo $? > $O/.a0 ) & fi
if [ -z "$P_" ]; then run sel_wrongtag tb_s81ph_sel "$SEL" "" "^RESULT PASS" -DTB_CTRL -DTB_MUT_WRONGTAG; echo $? > $O/.a1; else ( run sel_wrongtag tb_s81ph_sel "$SEL" "" "^RESULT PASS" -DTB_CTRL -DTB_MUT_WRONGTAG; echo $? > $O/.a1 ) & fi
if [ -z "$P_" ]; then run sel_mut2 tb_s81ph_sel "$SEL" "" "^RESULT PASS" -DTB_CTRL -DOT_S81_DW_MUT=2; echo $? > $O/.a2; else ( run sel_mut2 tb_s81ph_sel "$SEL" "" "^RESULT PASS" -DTB_CTRL -DOT_S81_DW_MUT=2; echo $? > $O/.a2 ) & fi
if [ -z "$P_" ]; then run sel_mut4 tb_s81ph_sel "$SEL" "" "^RESULT PASS" -DTB_CTRL -DOT_S81_DW_MUT=4; echo $? > $O/.a3; else ( run sel_mut4 tb_s81ph_sel "$SEL" "" "^RESULT PASS" -DTB_CTRL -DOT_S81_DW_MUT=4; echo $? > $O/.a3 ) & fi
wait; s0=$(cat $O/.a0); wait; s1=$(cat $O/.a1); wait; s2=$(cat $O/.a2); wait; s3=$(cat $O/.a3)
if [ -z "$P_" ]; then run col_base tb_s81ph_col "$COL" "+jobs=40" "^RESULT PASS" -DTB_CTRL; echo $? > $O/.b0; else ( run col_base tb_s81ph_col "$COL" "+jobs=40" "^RESULT PASS" -DTB_CTRL; echo $? > $O/.b0 ) & fi
if [ -z "$P_" ]; then run col_wrongtag tb_s81ph_col "$COL" "+jobs=40" "^RESULT PASS" -DTB_CTRL -DTB_MUT_WRONGTAG; echo $? > $O/.b1; else ( run col_wrongtag tb_s81ph_col "$COL" "+jobs=40" "^RESULT PASS" -DTB_CTRL -DTB_MUT_WRONGTAG; echo $? > $O/.b1 ) & fi
if [ -z "$P_" ]; then run col_mut2 tb_s81ph_col "$COL" "+jobs=40" "^RESULT PASS" -DTB_CTRL -DOT_S81_DW_MUT=2; echo $? > $O/.b2; else ( run col_mut2 tb_s81ph_col "$COL" "+jobs=40" "^RESULT PASS" -DTB_CTRL -DOT_S81_DW_MUT=2; echo $? > $O/.b2 ) & fi
if [ -z "$P_" ]; then run col_mut4 tb_s81ph_col "$COL" "+jobs=40" "^RESULT PASS" -DTB_CTRL -DOT_S81_DW_MUT=4; echo $? > $O/.b3; else ( run col_mut4 tb_s81ph_col "$COL" "+jobs=40" "^RESULT PASS" -DTB_CTRL -DOT_S81_DW_MUT=4; echo $? > $O/.b3 ) & fi
wait; c0=$(cat $O/.b0); wait; c1=$(cat $O/.b1); wait; c2=$(cat $O/.b2); wait; c3=$(cat $O/.b3)
v=PASS
[ $s0 -eq 0 ] && [ $c0 -eq 0 ] || v=FAIL
for x in $s1 $s2 $s3 $c1 $c2 $c3; do [ $x -eq 1 ] || v=FAIL; done
echo "SELCOL_CTRL_GATE $v sel base=$s0 wrongtag=$s1 mut2=$s2 mut4=$s3 | col base=$c0 wrongtag=$c1 mut2=$c2 mut4=$c3 | $(grep -h '^CTRL' $O/sel_base/run.log $O/col_base/run.log | tr '\n' ' ')" | tee $O/verdict.log
[ $v = PASS ]
