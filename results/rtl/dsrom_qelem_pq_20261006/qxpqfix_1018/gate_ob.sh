#!/bin/bash
# QXPQ-FIX 10-18 (S81.STA.LEAF.3.5): qxpq RSTP=1 closed recipe (calibrate cmd of dsrom-qelem-qs5f-rstp-f9192e143-tc-hm10-cl-2bded98f0)
# + OT_Q_CK_NORTH=1 (clk N centre) + OT_Q_PDH=dsrom_q_outflop_band.tcl (output pin-flop band at the pins) + HM 0.025
# (route.io_hold_margin >= 0.025 rule), stopped after CTS; then TT/FF insertion + layout PNGs.
# src = HF-1 gate src (RTL = closed RSTP view) + overlay of claude/qxpq-fix-1018 (cl_route_qs.sh, dsrom_q_outflop_band.tcl).
set -u
G=$(pwd); SRC=$G/src; RUN=$G/gate_run; O=$G/gate_post; mkdir -p $RUN $O
cd $SRC || exit 2
export OT_NATIVE_Q_H1_INPUT=1 OT_NATIVE_Q_H1_RST=1 OT_Q_EF_SOUTH=1 RSTP=1 OT_Q_CK_NORTH=1 OT_Q_PDH=physical/abi3/dsrom_q_outflop_band.tcl
TTB=/srv/opentallas-scratch/claude/ttbatch/26f14af32
export OT_TTB_CORNER_MARK=$RUN/ttb_corner.txt
python3 $TTB/tools/closure_loop/tt_overlay.py $SRC || exit 3
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl tools/dsrom_qelem_cl/native_q_h1r_hook.tcl'
export OT_ORFS_CORNER_OVERRIDE=TC
HM=0.025 QS=5 FH=221.4 RLA=0.12 THREADS=16 bash tools/dsrom_qelem_cl/cl_route_qs.sh gate_ob $RUN/routes --pnr-stop-after cts
echo "GATE_RC=$?"
B=$(ls -d $RUN/routes/jobs/gate_ob/work/orfs/results/asap7/*/base | head -1); echo "BASE $B"
grep -h 'OT_OUTFLOP ports\|OT_OUTFLOP worst\|OT_OUTFLOP skip' -r $RUN/routes/jobs/gate_ob/work/orfs/logs 2>/dev/null | sort | uniq -c | head -20
python3 tools/closure_loop/ck_insertion.py --base $B --clock core_clk --route-corner TC --output $O/ck.json > $O/ck.log 2>&1; echo "CK_RC=$?"
for t in floorplan:3_2_place_iop.odb placed:3_5_place_dp.odb cts:4_1_cts.odb; do
  tag=${t%%:*}; odb=${t#*:}
  printf 'read_db /base/%s\nsource /src/tools/ref_tile/layout_dump.tcl\nexit\n' $odb > $O/ld_$tag.tcl
  docker run --rm -e OT_LAYOUT_OUT=/o/layout_$tag.json -e OT_LAYOUT_CLOCKS=clk -e OT_LAYOUT_TOP=ot_v41_rom_elem_q_qxpq_w10 -v $B:/base:ro -v $SRC:/src:ro -v $O:/o openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /o/ld_$tag.tcl > $O/ld_$tag.log 2>&1
  echo "LAYOUT_$tag rc=$?"
  python3 tools/ref_tile/layout_png.py $O/layout_$tag.json $O/png_$tag --title "qxpq RSTP=1 ck-N + out-flop band gate $tag" > $O/png_$tag.log 2>&1; echo "PNG_$tag rc=$?"
done
python3 - $O/ck.json <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
for c in ('tt','ff'):
  b=d[c]['boundary']; a=d[c]['all']; print("CK",c,"boundary mean %.1f min %.1f max %.1f spread %.1f | all %.1f-%.1f n %d"%(b['mean'],b['min'],b['max'],b['max']-b['min'],a['min'],a['max'],a['n']))
PY
