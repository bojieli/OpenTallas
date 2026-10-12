#!/bin/bash
# [link] 2026-10-10 hfd_coll R25GQ die-view route (route_view.sh, variant r25gqn pinned ports, flat: the 9 ot_hcoll_port
# slices synthesized with the core, 162 x ot_sram_1r1w_128x256 placed by the flow).   route.sh <label> [extra args]
set -u
lab=$1; shift
C=rtl/hbm_accel/generic/collective; T=rtl/hbm_accel/tu
export SRC=${SRC:-$PWD} VARIANT=r25gqn OT_VIEW_PORTS_ROOT=physical/hbm_accel_die_views/ports_r25gqn CKP=refclk \
  IOAPP=physical/hbm_accel_die_views/coll_r25gq/io_extra.tcl NEED=${NEED:-96} \
  MACROS="ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2" HALO="${HALO:-4 4}" \
  POSTSDC="physical/hbm_accel_die_views/common/signoff_unc60.sdc physical/hbm_accel_die_views/common/vclk_corner_true.sdc" \
  SRCS="$C/ot_hfd_coll_r25gq.sv $C/ot_hgi_coll_ep.sv $C/ot_hgi_coll_amerge.sv $C/ot_hgi_coll_record.sv $C/ot_hgi_coll_decode.sv
        $C/rgx/ot_hgi_coll_rgx_hbm.sv $C/rgx/ot_hgi_coll_rgx_snk.sv $C/rgx/ot_hgi_coll_rgx.sv $C/rgx/ot_hgi_coll_rgx_src.sv
        $C/rgx/ot_hgi_coll_rgx_sink.sv rtl/hbm_accel/generic/peers/ot_hgi_hbm_lane.sv $T/ot_hbm_accel_tu_endpoint_psg.sv
        $T/ot_hcoll_sram_prims.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $T/ot_hcoll_port.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
        rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/link/ot_link_afifo.sv rtl/hbm_accel/generic/ot_hgi_cfg.sv
        physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv rtl/common/ot_fwd_link_stage.sv"
L=${L:-${CK_SS_MEAN:-770}}
bash physical/hbm_accel_die_views/common/make_io_vclk_margin.sh $L > /dev/null
export SDCA=physical/hbm_accel_die_views/common/io_vclk_m_$L.sdc
bash physical/hbm_accel_die_views/common/route_view.sh $lab hfd_coll physical/hbm_accel_die_views/coll_r25gq/rtl/hfd_coll.sv \
  --orfs-var VERILOG_INCLUDE_DIRS=/src/rtl/hbm_accel/generic "$@"
