#!/bin/bash
# stn_route.sh (CLAUDE HBM-ABSTRACTS stations) <src> <out> <label> <master> [PD] : one station view route via route_view.sh
S=$1; O=$2; lab=$3; m=$4; pd=${5:-0.55}; shift 5
cd $S
SRC=$S OUT=$O PD=$pd CORES=${CORES:-6} NEED=${NEED:-12} \
SRCS="rtl/common/ot_fwd_link_stage.sv rtl/common/ot_meso_fifo.sv physical/hbm_accel_die_views/stations/rtl/ot_hbm_stn_lib.sv" \
  physical/hbm_accel_die_views/common/route_view.sh $lab $m physical/hbm_accel_die_views/stations/$m/$m.sv \
  --orfs-var SDC_FILE=/src/physical/hbm_accel_die_views/stations/$m/$m.sdc --orfs-var SYNTH_KEEP_MODULES=ot_fwd_clk_inv --step-tcl POST_SYNTH=physical/hbm_accel_die_views/stations/bench/stn_post_synth.tcl --step-tcl PRE_CTS=physical/hbm_accel_die_views/stations/bench/stn_pre_cts.tcl "$@"
