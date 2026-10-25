#!/bin/bash
# TOK-FUNC-QW stage "head" (10-21): the TT head leaf (h16y/h16yb RTL = ot_qfd_tt_ctlm_static_hr_safe32 #(.H16X(2)))
# issuing a token's stages incl. the LM-head stage 37, on the RTL-only SOURCE ASSEMBLY (RUNROOT/src), Verilator 5.050.
#
#   stage_head.sh RUNROOT [--die-netlist DIR]
#
# Bench = the existing QLB-PROG / QLB-C4b head bench rtl/test/qwen_dv/tt_ctlm_prog_bench.py (compiled ctlm image loaded
# exactly as qfd_sys_face replays it; every slice command / LOCAL start / head fixed issue + END / ROM go / native go /
# XPF arm checked on its compiled edge).  Runs (all from RUNROOT/src, nothing generated, nothing from a netlist):
#   h16y_img0   h16y RTL parent (results/rtl/qw_head_safe32_1020/h16y/prepare_rtl_parent.py), image img0   -> PASS
#   h16y_imgh   same, image imgh (LM-head programme at base 25, stage 37)                                     -> PASS
#   h16y_bmut3  same build, imgh with the LM-head segment-G calendar's first row one cycle late               -> FAIL
#   src_landed  the die source as written (qfd_tt_ctlm_dv HARD_HR=1 = ot_qfd_tt_ctlm_static_hr) + the landed
#               cluster qfd_tt_ctlm_dv_lpf_lp in lockstep (--landed 1), image imgh                            -> PASS + LOCKSTEP
# Cycles: the LM-head span measured on RTL = stage-37 start edge -> the head's END issue (pc 29), and -> the LM-head ROM go
# (stage_head.collect.py); compared with the compiled image (lm_head.expected) and the ctlm plan price (3,101).
# The slices / ROM tiles / native unit are NOT simulated here: they answer at their compiled status cycles (image status
# timeline) -> listed in stand_ins.  The LM-head DATAPATH (18,992-row matvec, AMAX, gather) is the stg stage (STG lm).
#
# --die-netlist DIR (closure hook): DIR/head_leaf.v = the GEN die carve of u_hr (module $HEAD_NET_MODULE, default
#   ot_qfd_tt_ctlm_static_hr_safe32_native32_1r; optional DIR/helpers.sv).  The three h16y runs then use the native
#   vehicle (physical/ref_tile/qfd_tt_head_static_h16y/prepare_bench.py transformation on that file) and grade = die-netlist;
#   src_landed is skipped (it binds RTL by construction).
set -u
RUNROOT=$(readlink -f "$1"); shift
NET=""
LEAF=0
# --leaf DIR (TOK-QW 10-24): same vehicle as --die-netlist, but DIR/head_leaf.v (+ helpers.sv) is the DIE-SELECTED head leaf
#   RTL (the leaf the bound compute die instantiates: rtl/qwen_dv/headprep13/h16za/native32_1r_param.v +
#   native32_helpers.sv, module ot_qfd_tt_ctlm_static_hr_safe32_native32_1r, selected by tt_ctlm =
#   qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1 in physical/die_plan/qwen_compute/bind/bound_r8/bind.f).  The behavioural
#   h16y family is not on main (results/rtl/qw_r56_selected_head_1023/README.md) -> this is the RTL head run; grade is
#   "RTL-functional (die-selected leaf, source assembly)", never die-netlist.
while [ $# -gt 0 ]; do case "$1" in --die-netlist) NET=$(readlink -f "$2"); shift 2;;
  --leaf) NET=$(readlink -f "$2"); LEAF=1; shift 2;; *) echo "bad arg $1"; exit 2;; esac; done
SRC=$RUNROOT/src; S=$RUNROOT/head; FX=$S/fx; T=$S/tree; HERE=$(dirname "$(readlink -f "$0")")
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
[ -d "$FX/results" ] || { echo "missing fixtures $FX (results/rtl/qlb_c4b_1018/lmh_cal/codex_r1, qw_head_safe32_1020/h16y, macros_v2)"; exit 2; }
# symlink overlay: src + fixtures; the vehicle files the prepare scripts write are real files under head/tree only
rm -rf "$T" "$S/runs"; mkdir -p "$T/physical" "$S/runs"
for d in rtl tools configs; do cp -as "$SRC/$d" "$T/"; done
cp -as "$SRC/physical/." "$T/physical/"; cp -as "$FX/physical/." "$T/physical/"; cp -as "$FX/results" "$T/"
for f in rtl/qwen_dv/qfd_tt_ctlm_dv_safe32_h16y_parent.sv rtl/test/qwen_dv/tt_ctlm_dv_safe32_h16y_sources.f \
         rtl/test/qwen_dv/tt_ctlm_prog_safe32_h16y_bench.py rtl/qwen_dv/qfd_tt_ctlm_dv_native32_1r_parent.sv \
         rtl/test/qwen_dv/tt_ctlm_dv_native32_1r_sources.f rtl/test/qwen_dv/tb_qfd_tt_ctlm_native32_1r_prog.sv \
         rtl/test/qwen_dv/tt_ctlm_prog_native32_1r_bench.py; do rm -f "$T/$f"; done
# the bench resolves ROOT from its own (symlink-resolved) path: make the stock bench a real file so ROOT = head/tree
rm -f "$T/rtl/test/qwen_dv/tt_ctlm_prog_bench.py"; cp "$SRC/rtl/test/qwen_dv/tt_ctlm_prog_bench.py" "$T/rtl/test/qwen_dv/"
cd "$T" || exit 3
IMG=results/rtl/qlb_c4b_1018/lmh_cal/codex_r1
R=$S/runs; A=(--decode 3 --hard 1 --segcal 1)
if [ -z "$NET" ]; then
  GRADE="RTL-functional (source assembly)"
  python3 results/rtl/qw_head_safe32_1020/h16y/prepare_rtl_parent.py > $R/prepare.log 2>&1 || { cat $R/prepare.log; exit 2; }
  B=rtl/test/qwen_dv/tt_ctlm_prog_safe32_h16y_bench.py
else
  GRADE="die-netlist"; [ $LEAF = 1 ] && GRADE="RTL-functional (die-selected leaf, source assembly)"
  rm -rf $S/net; mkdir -p $S/net; cp "$NET/head_leaf.v" $S/net/native32_1r_param.v
  if [ -f "$NET/helpers.sv" ]; then cp "$NET/helpers.sv" $S/net/native32_helpers.sv; else cp results/rtl/qw_head_safe32_1020/h16y/net_ifg2/native32_helpers.sv $S/net/; fi
  sed -e "s#Path('results/rtl/qw_head_safe32_1020/h16y/net_ifg2')#Path('$S/net')#" \
      -e "s#name = 'ot_qfd_tt_ctlm_static_hr_safe32_native32_1r'#name = '${HEAD_NET_MODULE:-ot_qfd_tt_ctlm_static_hr_safe32_native32_1r}'#" \
      physical/ref_tile/qfd_tt_head_static_h16y/prepare_bench.py > $S/net/prepare_bench.py
  python3 $S/net/prepare_bench.py > $R/prepare.log 2>&1 || { cat $R/prepare.log; exit 2; }
  B=rtl/test/qwen_dv/tt_ctlm_prog_native32_1r_bench.py
fi
# img0 | imgh then bmut3 (same obj) | literal die source + landed lockstep -- three Verilator builds in parallel
( python3 $B "${A[@]}" --work $R/h16y_img0 --img $IMG/img0 > $R/h16y_img0.out 2>&1; echo "RC $?" >> $R/h16y_img0.out ) &
( python3 $B "${A[@]}" --work $R/h16y_imgh --img $IMG/imgh > $R/h16y_imgh.out 2>&1; echo "RC $?" >> $R/h16y_imgh.out
  python3 $B "${A[@]}" --work $R/h16y_imgh --img $IMG/imgh --bmut 3 > $R/h16y_bmut3.out 2>&1; echo "RC $?" >> $R/h16y_bmut3.out ) &
if [ -z "$NET" ]; then
  ( python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py "${A[@]}" --landed 1 --work $R/src_landed --img $IMG/imgh > $R/src_landed.out 2>&1
    echo "RC $?" >> $R/src_landed.out ) &
fi
wait
for f in $R/*.out; do echo "$(basename $f .out): $(grep -E 'CTLM_PROG .*(PASS|FAIL)|LANDED_LOCKSTEP' $f | tr '\n' ' ')"; done | tee $R/summary.txt
python3 "$HERE/stage_head.collect.py" "$RUNROOT" "$GRADE" "$IMG"
