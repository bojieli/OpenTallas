#!/bin/bash
# closure-loop hbm_coll_port_capture-lvt-bbe601a79-tc-routine stage calibrate attempt 1
set -o pipefail
export RUN=/srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine
export SRC=/srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src
export CL=/srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl
export HOST=ot-pve1
export NAME=hbm_coll_port_capture_lvt_bbe601a79_tc_routine
export LABEL=hbm_coll_port_capture_lvt_bbe601a79_tc_routine
export RAW_NAME=hbm_coll_port_capture-lvt-bbe601a79-tc-routine
export BLOCK=ot_hcoll_port
export COMMIT=bbe601a7934ea5dabf0e8e4668b25b40bee52c0e
export THREADS=8
export CL_PHASE=calibrate
export CL_LABEL_SUFFIX=_cal
export CL_STOP_AFTER='--pnr-stop-after cts'
mkdir -p /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/bin && cat > /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/bin/docker <<'OT_DOCKER_SHIM'
#!/bin/bash
# closure-loop shim: every container gets LEC_CHECK=0 (kepler-formal needs AVX-512); then the real docker
for e in ${PATH//:/ }; do
  if [ -x "$e/docker" ] && ! [ "$e/docker" -ef "$0" ]; then
    if [ "${1:-}" = run ] && [ -n "${OT_FP_LINT_DIR:-}" ]; then
      # FP-LINT: the floorplan margin lint (ORFS PRE GLOBAL_PLACE) sees OT_FP_LINT and writes its verdict to /ot_fplint
      mkdir -p "$OT_FP_LINT_DIR"; shift
      # PREROUTE-GATE: the pre-route timing gate (ORFS POST DETAIL_PLACE) sees OT_PREROUTE_GATE, writes PREROUTE_FAIL there
      exec "$e/docker" run -e LEC_CHECK=0 -e OT_FP_LINT -e OT_FP_LINT_ARGS -e OT_PREROUTE_GATE -e OT_PREROUTE_GATE_ARGS \
        -e OT_ABC_NO_DCH -v "$OT_FP_LINT_DIR:/ot_fplint" "$@"
    fi
    # ABC-NODCH (drive-2155): a recipe exporting OT_ABC_NO_DCH=1 gets &synch2 for &dch (tools/orfs_hold_mm.py)
    if [ "${1:-}" = run ]; then shift; exec "$e/docker" run -e LEC_CHECK=0 -e OT_ABC_NO_DCH "$@"; fi
    exec "$e/docker" "$@"
  fi
done
echo "closure-loop docker shim: no docker on PATH" >&2; exit 127
OT_DOCKER_SHIM
chmod +x /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/bin/docker
export PATH=/srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/bin:$PATH
ship_fpl() { for f in fp_margin_lint.py fp_margin_lint.tcl orfs_hold_mm.py orfs_hold_mm.tcl preroute_gate.py preroute_gate.tcl; do [ -f /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/$f ] && [ -d /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src/tools ] && cp -f /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/$f /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src/tools/$f; done; for fh in /srv/opentallas-scratch/claude/flowhold/src /home/ubuntu/closure-loop-local/flowhold/src; do for fd in orfs_hold_mm.py:tools orfs_hold_mm.tcl:tools h1_patch.py:tools/closure_loop hold_corners_patch.py:tools/closure_loop; do f=${fd%%:*}; t=$fh/${fd#*:}; [ -f /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/$f ] && [ -d $t ] && ! cmp -s /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/$f $t/$f && cp -f /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/$f $t/.$f.$$ && mv -f $t/.$f.$$ $t/$f; done; done; for fh in /srv/opentallas-scratch/claude/ttbatch/26f14af32 /home/ubuntu/closure-loop-local/ttbatch/26f14af32; do for fd in tt_overlay.py:tools/closure_loop h1_patch.py:tools/closure_loop cg_pushdown.tcl:physical/common_flow clk_net_protect.tcl:physical/common_flow link_budget_hook.tcl:physical/common_flow link_budget_consistent.sdc:physical/common_flow nbr_clk_measured_ttb.sdc:physical/common_flow; do f=${fd%%:*}; t=$fh/${fd#*:}; [ -f /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/$f ] && [ -d $t ] && ! cmp -s /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/$f $t/$f && cp -f /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/$f $t/.$f.$$ && mv -f $t/.$f.$$ $t/$f; done; done; true; }
ship_fpl
rm -rf /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/fplint/calibrate.a1 && mkdir -p /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/fplint/calibrate.a1 && chmod a+rwx /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/fplint/calibrate.a1
export OT_FP_LINT_DIR=/srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/fplint/calibrate.a1
export OT_FP_LINT=1 OT_FP_LINT_DIR=/srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/fplint/calibrate.a1 OT_FP_LINT_ARGS=''
export OT_CAL_CTS_ONLY=1
python3 /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/hold_corners_patch.py /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src
export OT_ORFS_CORNER=TC
export OT_CAL_ROUTE_CORNER=TC
export HM=0.01
export OT_ROUTE_HOLD_CORNERS=mm
python3 /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/hold_corners_patch.py /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src
mkdir -p /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src/.ot_mm && cp /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/io_ref_routed.sdc /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src/.ot_mm/ff_ioref_last.sdc
mkdir -p /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src/.ot_mm
cp /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/io_ref_routed.sdc /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src/.ot_mm/
export OT_MM_FF_SDC=.ot_mm/io_ref_routed.sdc
python3 -c "from tools.hbm_coll_capture_placement_model import model; import json; print(json.dumps(model()))" && export OT_MULTI_VT=lvt OT_ORFS_CORNER_OVERRIDE=TC OT_ROUTE_HOLD_CORNERS=mm OT_TTB_CORNER_MARK=/srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/ttb_corner.txt && python3 tools/closure_loop/hold_corners_patch.py /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src && python3 "$(test -f tools/closure_loop/tt_overlay.py && echo tools/closure_loop/tt_overlay.py || ls -d /srv/opentallas-scratch/claude/ttbatch/26f14af32/tools/closure_loop/tt_overlay.py /home/ubuntu/closure-loop-local/ttbatch/26f14af32/tools/closure_loop/tt_overlay.py 2>/dev/null | head -1)" /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src && export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'; python3 tools/closure_loop/h1_patch.py /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/src && CAPTURE_ADJACENT=1 INTERIOR=1 DIEW=480 DIEH=540 PHALO='4 10' OUT=/srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/routes CORES=8 PD=0.45 bash physical/hbm_accel_die_views/coll/rtl_ps/route_ps.sh hbm_coll_port_capture_lvt_bbe601a79_tc_routine${CL_LABEL_SUFFIX} port $CL_STOP_AFTER
B=$(ls -d /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/routes/hbm_coll_port_capture_lvt_bbe601a79_tc_routine_cal/work/orfs/results/asap7/*/base 2>/dev/null | tail -1); [ -n "$B" ] || { echo 'calibrate: no ORFS base /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/routes/hbm_coll_port_capture_lvt_bbe601a79_tc_routine_cal/work/orfs/results/asap7/*/base'; bash /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/cal_classify.sh '/srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/routes/hbm_coll_port_capture_lvt_bbe601a79_tc_routine_cal/work/orfs/results/asap7/*/base'; exit 3; }
[ -f "$B/4_1_cts.odb" ] || { echo "calibrate: no 4_1_cts.odb under $B"; bash /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/cal_classify.sh '/srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/routes/hbm_coll_port_capture_lvt_bbe601a79_tc_routine_cal/work/orfs/results/asap7/*/base'; exit 4; }
python3 /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/ck_insertion.py --base "$B" --clock core_clk --output /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/calib.json --route-corner "${OT_CAL_ROUTE_CORNER:-}" > /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/calib.env || exit 4
cat /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/calib.env
set -a; . /srv/opentallas-scratch/claude/closure-loop/hbm_coll_port_capture-lvt-bbe601a79-tc-routine/cl/calib.env; set +a
bash physical/hbm_accel_die_views/common/make_io_vclk.sh $CK_SS_MEAN && bash physical/hbm_accel_die_views/common/make_io_vclk_ff.sh $CK_FF_MIN $CK_FF_MAX
