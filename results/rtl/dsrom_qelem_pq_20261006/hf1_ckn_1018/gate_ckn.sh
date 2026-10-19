#!/bin/bash
# HF-1 10-18: qxpq RSTP=1 closed recipe (calibrate-stage cmd of dsrom-qelem-qs5f-rstp-f9192e143-tc-hm10-cl-2bded98f0)
# + OT_Q_CK_NORTH=1 (clk at N-face centre), stopped after CTS; then TT/FF insertion + layout PNGs.
# src = epyc4 qxpq-rst-1017/src_gate (86727ef86, RTL = closed) + overlay of 6d2e178a4 launch.sh, tools/closure_loop, tools/ref_tile.
set -u
G=$(pwd); SRC=$G/src; RUN=$G/gate_run; O=$G/gate_post; mkdir -p $RUN $O
cd $SRC || exit 2
export OT_NATIVE_Q_H1_INPUT=1 OT_NATIVE_Q_H1_RST=1 OT_Q_EF_SOUTH=1 RSTP=1 OT_Q_CK_NORTH=1
TTB=/srv/opentallas-scratch/claude/ttbatch/26f14af32
export OT_TTB_CORNER_MARK=$RUN/ttb_corner.txt
python3 $TTB/tools/closure_loop/tt_overlay.py $SRC || exit 3
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl tools/dsrom_qelem_cl/native_q_h1r_hook.tcl'
export OT_ORFS_CORNER_OVERRIDE=TC
HM=0.010 QS=5 FH=221.4 RLA=0.12 THREADS=16 bash tools/dsrom_qelem_cl/cl_route_qs.sh gate_ckn $RUN/routes --pnr-stop-after cts
echo "GATE_RC=$?"
B=$(ls -d $RUN/routes/jobs/gate_ckn/work/orfs/results/asap7/*/base | head -1); echo "BASE $B"
python3 tools/closure_loop/ck_insertion.py --base $B --clock core_clk --route-corner TC --output $O/ck.json > $O/ck.log 2>&1; echo "CK_RC=$?"
for t in floorplan:3_2_place_iop.odb placed:3_5_place_dp.odb cts:4_1_cts.odb; do
  tag=${t%%:*}; odb=${t#*:}
  printf 'read_db /base/%s\nsource /src/tools/ref_tile/layout_dump.tcl\nexit\n' $odb > $O/ld_$tag.tcl
  docker run --rm -e OT_LAYOUT_OUT=/o/layout_$tag.json -e OT_LAYOUT_CLOCKS=clk -e OT_LAYOUT_TOP=ot_v41_rom_elem_q_qxpq_w10 -v $B:/base:ro -v $SRC:/src:ro -v $O:/o openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /o/ld_$tag.tcl > $O/ld_$tag.log 2>&1
  echo "LAYOUT_$tag rc=$?"
  python3 tools/ref_tile/layout_png.py $O/layout_$tag.json $O/png_$tag --title "qxpq RSTP=1 ck-N gate $tag" > $O/png_$tag.log 2>&1; echo "PNG_$tag rc=$?"
done
python3 - $O/ck.json <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
for c in ('tt','ff'):
  b=d[c]['boundary']; a=d[c]['all']; print("CK",c,"boundary mean %.1f min %.1f max %.1f spread %.1f | all %.1f-%.1f n %d"%(b['mean'],b['min'],b['max'],b['max']-b['min'],a['min'],a['max'],a['n']))
PY
