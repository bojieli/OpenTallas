#!/bin/bash
# [link] 2026-10-10 hfd_lk_ep die-view route at the R25GQ slot (route_view.sh: die pins at the generator positions,
# variant r25gqn) with the 3 closed retry macros (view_wpin_hm10; RVIEW=<dir> selects another closed view, e.g. the NAK_HOLD 64
# rebuild physical/hbm_link_retry_pipeline_20261009/view_wpin_nakh64_hm10) placed by macro_place.tcl; die-pin flops anchored at
# their pins (io_flop_at_pins / out_flop_release).
#   route.sh <label> [extra run_abi3_physical args]   env: OUT, CORES, PD (0.55), HM (0.010), WSF (wire-stage density),
#   DH_OVR (trial outline height; route_view.sh)
set -u
lab=$1; shift
export SRC=${SRC:-$PWD} VARIANT=r25gqn OT_VIEW_PORTS_ROOT=physical/hbm_accel_die_views/ports_r25gqn CKP="clk*" \
  SRCS="rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/hbm_accel/tu/lk_ep_20261010/ot_crc_par.sv rtl/hbm_accel/tu/lk_ep_20261010/ot_hbm_lk_ep.sv" \
  PDN=${PDN:-physical/hbm_accel_die_views/common/pdn_view_hier.tcl} MACROS="ot_hbm_link_retry_pipeline=${RVIEW:-physical/hbm_link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline}" HALO="${HALO:-8 8}" \
  POSTSDC="physical/hbm_accel_die_views/common/signoff_unc60.sdc physical/hbm_accel_die_views/common/vclk_corner_true.sdc"
L=${L:-${CK_SS_MEAN:-770}}
bash physical/hbm_accel_die_views/common/make_io_vclk_margin.sh $L > /dev/null
export SDCA=physical/hbm_accel_die_views/common/io_vclk_m_$L.sdc
bash physical/hbm_accel_die_views/common/route_view.sh $lab hfd_lk_ep rtl/hbm_accel/tu/lk_ep_20261010/hfd_lk_ep.sv \
  --orfs-var MACRO_PLACEMENT_TCL=/src/physical/hbm_lk_ep_20261010/${MPL:-macro_place.tcl} \
  --step-tcl PRE_GLOBAL_PLACE=physical/qwen_die_masters/io_flop_at_pins.tcl --step-tcl PRE_DETAIL_PLACE=physical/qwen_die_masters/out_flop_release.tcl "$@"
