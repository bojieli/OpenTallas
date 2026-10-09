#!/bin/bash
# closure-loop hbm_loader_ldiv_B_v3-d74d0faa7-cl stage calibrate attempt 1
set -o pipefail
export RUN=/srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl
export SRC=/srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/src
export CL=/srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl
export HOST=ot-epyc2
export NAME=hbm_loader_ldiv_B_v3_d74d0faa7_cl
export LABEL=hbm_loader_ldiv_B_v3_d74d0faa7_cl
export RAW_NAME=hbm_loader_ldiv_B_v3-d74d0faa7-cl
export BLOCK=hfd_loader
export COMMIT=d74d0faa7ff49d0f86e2e5cc940dece03f185d2d
export THREADS=12
export CL_PHASE=calibrate
export CL_LABEL_SUFFIX=_cal
export CL_STOP_AFTER='--pnr-stop-after cts'
mkdir -p /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/bin && cat > /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/bin/docker <<'OT_DOCKER_SHIM'
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
chmod +x /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/bin/docker
export PATH=/srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/bin:$PATH
ship_fpl() { for f in fp_margin_lint.py fp_margin_lint.tcl orfs_hold_mm.py orfs_hold_mm.tcl preroute_gate.py preroute_gate.tcl; do [ -f /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/$f ] && [ -d /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/src/tools ] && cp -f /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/$f /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/src/tools/$f; done; for fh in /srv/opentallas-scratch/claude/flowhold/src /home/ubuntu/closure-loop-local/flowhold/src; do for fd in orfs_hold_mm.py:tools orfs_hold_mm.tcl:tools h1_patch.py:tools/closure_loop hold_corners_patch.py:tools/closure_loop; do f=${fd%%:*}; t=$fh/${fd#*:}; [ -f /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/$f ] && [ -d $t ] && ! cmp -s /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/$f $t/$f && cp -f /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/$f $t/.$f.$$ && mv -f $t/.$f.$$ $t/$f; done; done; for fh in /srv/opentallas-scratch/claude/ttbatch/26f14af32 /home/ubuntu/closure-loop-local/ttbatch/26f14af32; do for fd in tt_overlay.py:tools/closure_loop h1_patch.py:tools/closure_loop cg_pushdown.tcl:physical/common_flow clk_net_protect.tcl:physical/common_flow link_budget_hook.tcl:physical/common_flow link_budget_consistent.sdc:physical/common_flow nbr_clk_measured_ttb.sdc:physical/common_flow; do f=${fd%%:*}; t=$fh/${fd#*:}; [ -f /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/$f ] && [ -d $t ] && ! cmp -s /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/$f $t/$f && cp -f /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/$f $t/.$f.$$ && mv -f $t/.$f.$$ $t/$f; done; done; true; }
ship_fpl
rm -rf /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/fplint/calibrate.a1 && mkdir -p /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/fplint/calibrate.a1 && chmod a+rwx /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/fplint/calibrate.a1
export OT_FP_LINT_DIR=/srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/fplint/calibrate.a1
export OT_FP_LINT=1 OT_FP_LINT_DIR=/srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/fplint/calibrate.a1 OT_FP_LINT_ARGS=''
export OT_CAL_CTS_ONLY=1
python3 /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/hold_corners_patch.py /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/src
export OT_ORFS_CORNER=TC
export OT_CAL_ROUTE_CORNER=TC
export HM=0.025
export OT_ROUTE_HOLD_CORNERS=mm
python3 /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/hold_corners_patch.py /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/src
mkdir -p /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/src/.ot_mm && cp /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/io_ref_routed.sdc /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/src/.ot_mm/ff_ioref_last.sdc
mkdir -p /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/src/.ot_mm
cp /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/io_ref_routed.sdc /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/src/.ot_mm/
export OT_MM_FF_SDC='physical/hbm_accel_die_views/common/signoff_unc60.sdc physical/hbm_accel_die_views/common/vclk_corner_true.sdc physical/hbm_accel_die_views/common/io_min/io_min_hfd_loader.sdc physical/hbm_accel_die_views/loader/sdc/hfd_loader_div.sdc .ot_mm/io_ref_routed.sdc'
export OT_ORFS_CORNER_OVERRIDE=TC; export OT_MM_FF_SDC='physical/hbm_accel_die_views/common/signoff_unc60.sdc physical/hbm_accel_die_views/common/vclk_corner_true.sdc physical/hbm_accel_die_views/common/io_min/io_min_hfd_loader.sdc physical/hbm_accel_die_views/loader/sdc/hfd_loader_div_v3.sdc' OT_CTS_FIX_HOOKS='physical/common_flow/clk_net_protect.tcl'; SRC="/srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/src" OUT="/srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/routes" PD="0.45" CORES="12" NEED="60" PER="0.833" IOF="0.2" MAXL="M7" SDCA="physical/hbm_accel_die_views/common/io_vclk_m_${CK_SS_MEAN:-770}.sdc" POSTSDC="physical/hbm_accel_die_views/common/signoff_unc60.sdc physical/hbm_accel_die_views/common/vclk_corner_true.sdc physical/hbm_accel_die_views/common/io_min/io_min_hfd_loader.sdc physical/hbm_accel_die_views/loader/sdc/hfd_loader_div_v3.sdc" FCP="5" PRECTS="physical/hbm_accel_die_views/common/pre_cts_fclk_root_buf.tcl" CTSA="-sink_clustering_enable -repair_clock_nets -balance_levels -sink_clustering_size 40 -sink_clustering_max_diameter 60 -distance_between_buffers 100 -apply_ndr none" SRCS="physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv rtl/hdc/ot_hdc_prefix.sv physical/hbm_accel_die_views/loader/rtl/ot_hfd_loader_host_m.sv physical/hbm_accel_die_views/loader/rtl/ot_hfd_loader_div.sv rtl/lib/ot_reset_sync.sv physical/hbm_accel_die_views/loader/rtl/ot_hfd_loader_m.sv physical/hbm_accel_die_views/loader/rtl/ot_hfd_store_m.sv rtl/hbm_accel/loader/ot_hbm_accel_dma64.sv rtl/gpu_sys/ot_gpu_cdc_fifo.sv rtl/link/ot_link_afifo.sv rtl/common/ot_fwd_link_stage.sv" physical/hbm_accel_die_views/common/route_view.sh hbm_loader_ldiv_B_v3_d74d0faa7_cl${CL_LABEL_SUFFIX} hfd_loader physical/hbm_accel_die_views/loader/rtl/hfd_loader_div.sv --orfs-var "SYNTH_KEEP_MODULES=ot_hfd_oreg1 ot_hfd_oreg2 ot_hfd_oreg3 ot_hfd_oreg4 ot_hfd_oreg5 ot_hfd_sink1 ot_hfd_rsync" --step-tcl POST_CTS=physical/hbm_accel_die_views/common/post_cts_vclk.tcl --sdc-append physical/hbm_accel_die_views/loader/sdc/hfd_loader_div_v3.sdc $CL_STOP_AFTER
B=$(ls -d /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/routes/hbm_loader_ldiv_B_v3_d74d0faa7_cl_cal/work/orfs/results/asap7/*/base 2>/dev/null | tail -1); [ -n "$B" ] || { echo 'calibrate: no ORFS base /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/routes/hbm_loader_ldiv_B_v3_d74d0faa7_cl_cal/work/orfs/results/asap7/*/base'; bash /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/cal_classify.sh '/srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/routes/hbm_loader_ldiv_B_v3_d74d0faa7_cl_cal/work/orfs/results/asap7/*/base'; exit 3; }
[ -f "$B/4_1_cts.odb" ] || { echo "calibrate: no 4_1_cts.odb under $B"; bash /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/cal_classify.sh '/srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/routes/hbm_loader_ldiv_B_v3_d74d0faa7_cl_cal/work/orfs/results/asap7/*/base'; exit 4; }
python3 /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/ck_insertion.py --base "$B" --clock core_clk --output /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/calib.json --route-corner "${OT_CAL_ROUTE_CORNER:-}" > /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/calib.env || exit 4
cat /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/calib.env
set -a; . /srv/opentallas-data/claude/closure-loop/hbm_loader_ldiv_B_v3-d74d0faa7-cl/cl/calib.env; set +a
physical/hbm_accel_die_views/common/make_io_vclk_margin.sh $CK_SS_MEAN && ls physical/hbm_accel_die_views/common/io_vclk_m_$CK_SS_MEAN.sdc
