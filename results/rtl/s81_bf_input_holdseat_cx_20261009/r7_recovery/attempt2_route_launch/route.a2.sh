#!/bin/bash
# closure-loop bfk_recut_hs4_sm15-c674dadfd-tc-cx stage route attempt 2
set -o pipefail
export RUN=/srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx
export SRC=/srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/src
export CL=/srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl
export HOST=ot-epyc4
export NAME=bfk_recut_hs4_sm15_c674dadfd_tc_cx
export LABEL=bfk_recut_hs4_sm15_c674dadfd_tc_cx
export RAW_NAME=bfk_recut_hs4_sm15-c674dadfd-tc-cx
export BLOCK=ot_s81_bf_native
export COMMIT=c674dadfd6eea63850ca61d7fb5470ca5bc55add
export THREADS=16
export CL_PHASE=route
export CL_LABEL_SUFFIX=''
export CL_STOP_AFTER=''
mkdir -p /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/bin && cat > /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/bin/docker <<'OT_DOCKER_SHIM'
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
chmod +x /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/bin/docker
export PATH=/srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/bin:$PATH
ship_fpl() { for f in fp_margin_lint.py fp_margin_lint.tcl orfs_hold_mm.py orfs_hold_mm.tcl preroute_gate.py preroute_gate.tcl; do [ -f /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/$f ] && [ -d /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/src/tools ] && cp -f /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/$f /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/src/tools/$f; done; for fh in /srv/opentallas-scratch/claude/flowhold/src /home/ubuntu/closure-loop-local/flowhold/src; do for fd in orfs_hold_mm.py:tools orfs_hold_mm.tcl:tools h1_patch.py:tools/closure_loop hold_corners_patch.py:tools/closure_loop; do f=${fd%%:*}; t=$fh/${fd#*:}; [ -f /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/$f ] && [ -d $t ] && ! cmp -s /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/$f $t/$f && cp -f /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/$f $t/.$f.$$ && mv -f $t/.$f.$$ $t/$f; done; done; for fh in /srv/opentallas-scratch/claude/ttbatch/26f14af32 /home/ubuntu/closure-loop-local/ttbatch/26f14af32; do for fd in tt_overlay.py:tools/closure_loop h1_patch.py:tools/closure_loop cg_pushdown.tcl:physical/common_flow clk_net_protect.tcl:physical/common_flow link_budget_hook.tcl:physical/common_flow link_budget_consistent.sdc:physical/common_flow nbr_clk_measured_ttb.sdc:physical/common_flow; do f=${fd%%:*}; t=$fh/${fd#*:}; [ -f /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/$f ] && [ -d $t ] && ! cmp -s /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/$f $t/$f && cp -f /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/$f $t/.$f.$$ && mv -f $t/.$f.$$ $t/$f; done; done; true; }
ship_fpl
rm -rf /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/fplint/route.a2 && mkdir -p /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/fplint/route.a2 && chmod a+rwx /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/fplint/route.a2
export OT_FP_LINT_DIR=/srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/fplint/route.a2
export OT_FP_LINT=1 OT_FP_LINT_DIR=/srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/fplint/route.a2 OT_FP_LINT_ARGS='--set sliver_um=10.0'
export OT_PREROUTE_GATE=1 OT_PREROUTE_GATE_ARGS=''
export HM=0.0
if [ -e /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/routes/bfk_recut_hs4_sm15_c674dadfd_tc_cx ]; then a=/srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/routes/bfk_recut_hs4_sm15_c674dadfd_tc_cx.attempt1; [ -e "$a" ] && a="$a.$(date +%s)"; mv /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/routes/bfk_recut_hs4_sm15_c674dadfd_tc_cx "$a"; fi
export OT_ORFS_CORNER=TC
export OT_ROUTE_HOLD_CORNERS=mm
python3 /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/hold_corners_patch.py /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/src
mkdir -p /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/src/.ot_mm && cp /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/io_ref_routed.sdc /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/src/.ot_mm/ff_ioref_last.sdc
mkdir -p /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/src/.ot_mm
cp /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/io_ref_routed.sdc /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/src/.ot_mm/
export OT_MM_FF_SDC='physical/s81_native_bf/margin/signoff_ref.sdc .ot_mm/io_ref_routed.sdc'
[ -f /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/calib.json ] || echo '{"calibrate": "disabled"}' > /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/calib.json
[ -f /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/calib.env ] && { set -a; . /srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/cl/calib.env; set +a; }
export OT_ORFS_CORNER_OVERRIDE=TC; export OT_MM_FF_SDC='physical/s81_native_bf/margin/signoff_ref.sdc'; OUT=/srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/routes SRC=/srv/opentallas-scratch2/scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx/src BF_VAR=recut bash physical/s81_native_bf/margin/route_var.sh bfk_recut_hs4_sm15_c674dadfd_tc_cx --hold-margin-ns 0.000 --param CG=0 --param INPUT_HOLD_SEATS=4 --orfs-var SETUP_SLACK_MARGIN=15
