#!/bin/bash
# HBM-FORM-SPLIT-14-SUX: make the 4 RE-FORM kits on epyc2 scratch3 from the HBM-FORM-SPLIT-13 kits (inputs only)
set -e
S=/srv/opentallas-scratch3/claude/hbm-form-split-14-sux; KS=/srv/opentallas-scratch2/claude/hbm-form-split-14-sux/kits; K13=/srv/opentallas-scratch2/claude/hbm-form-split-13
XD=$K13/ot_hbm_su_pg_lane_exp_x_core/ot_hbm_su_pg_lane_exp_x_core_vD
FB=$K13/ot_hbm_su_pg_lane_full_x_core/ot_hbm_su_pg_lane_full_x_core_vB
EX='--exclude=run --exclude=signoff --exclude=lec --exclude=lec_async.lock --exclude=lec_async.on --exclude=lec_async.owner --exclude=lec_async.pid --exclude=lec_async.runs --exclude=lec_async.source_identity --exclude=lec_async.identity --exclude=lec_async.ready --exclude=lec_async.done --exclude=lec_async.rc --exclude=*.log --exclude=rtl_lint.json --exclude=rtl_lint.ys --exclude=selrange.json --exclude=selrange.rc --exclude=face_guard.json --exclude=port_bind.json --exclude=postcts_gate_*.json --exclude=hold_census.txt --exclude=pin_audit.json --exclude=placed.csv --exclude=physical_completion --exclude=views --exclude=__pycache__ --exclude=FAIL_* --exclude=sdc_lint.json --exclude=*.previous.* --exclude=eco_* --exclude=lec_run.log'
mk() { # SRC DST
  rm -rf $2; mkdir -p $2; rsync -a $EX $1/ $2/
  cp $S/repo/results/die_hbm_1106/sux/sux_latbal.tcl $2/sux_latbal.tcl
  python3 -I - $2/post_cts_setup.tcl <<'PY'
import sys; p=sys.argv[1]; t=open(p).read(); a="source {/work/f4_chain_leaf.tcl}\n"
assert t.count(a)==1
t=t.replace(a, a+"# HBM-FORM-SPLIT-14-SUX 11-06: post-CTS subtree latency balance to the latest sink (clock form; sux_latbal.tcl header)\nsource {/work/sux_latbal.tcl}\n")
open(p,'w').write(t)
PY
}
mc() { sed "s/^module $2 #(/module $2__mc #(/" $1 > $3; grep -q "^module $2__mc #(" $3; }
D=$S/gen_xd
# exp_x vE = vA: vD kit (vC RTL, plain TritonCTS tree) + latency balance
E=$KS/ot_hbm_su_pg_lane_exp_x_core_vE; mk $XD $E
# exp_x vF = vB: + MLAT 7 (C1+C2+C3+C5) lane
F=$KS/ot_hbm_su_pg_lane_exp_x_core_vF; mk $XD $F
cp $D/ot_hbm_su_static_lane_xb.sv $D/ot_hbm_su_static_lane_pinreg_xb.sv $F/rtl/
mc $D/ot_hbm_su_pg_lane_exp_x_core.sv ot_hbm_su_pg_lane_exp_x_core $F/rtl/ot_hbm_su_pg_lane_exp_x_core.sv
# full_x vC = vA: full_x vB kit RTL (MLAT 5 / ALAT 4) + plain tree + latency balance
C=$KS/ot_hbm_su_pg_lane_full_x_core_vC; mk $FB $C
# full_x vD = vB: + MLAT 7 / ALAT 5 lane
V=$KS/ot_hbm_su_pg_lane_full_x_core_vD; mk $FB $V
cp $D/ot_hbm_su_static_lane_xb.sv $D/ot_hbm_su_static_lane_pinreg_xb.sv $V/rtl/
mc $D/ot_hbm_su_pg_lane_full_x_core.sv ot_hbm_su_pg_lane_full_x_core $V/rtl/ot_hbm_su_pg_lane_full_x_core.sv
for k in $C $V; do
cp $XD/pre_cts_none.tcl $k/
cat >> $k/config.mk <<'CFG'

# HBM-FORM-SPLIT-14-SUX 2026-11-06: clock form = ONE plain TritonCTS tree (no density taps / tap align, as exp_x vD: its placement-RC
# tree predicts the routed one, 265-438 -> 274-466, while the density-tap kits' routed tail 590-640 was invisible post-CTS 381-486)
# + post-CTS subtree latency balance to the latest sink (sux_latbal.tcl, sourced in post_cts_setup.tcl).
override export PRE_CTS_TCL = /work/pre_cts_none.tcl
override export OT_F4_NEXT_TCL = /work/tap_balance.tcl
CFG
done
echo "# HBM-FORM-SPLIT-14-SUX vD: RTL = results/die_hbm_1106/sux/gen_lane_xd.py (MLAT 7 = C1+C2+C3+C5 / ALAT 5)" >> $V/config.mk
for k in $E $F $C $V; do
  grep -q "OT_HOLD_REPAIR_SCOPE = reg2reg" $k/config.mk || echo "export OT_HOLD_REPAIR_SCOPE = reg2reg" >> $k/config.mk
  echo "$k $(du -sh $k | cut -f1) $(ls $k/rtl | wc -l) rtl files"
done
