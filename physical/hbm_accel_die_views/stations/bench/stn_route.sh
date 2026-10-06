#!/bin/bash
# stn_route.sh (CLAUDE HBM-ABSTRACTS stations) <src> <out> <label> <master> [PD] : one station view route via route_view.sh
# env FENCE=1: compact region per meso FIFO (bench/stn_meso_fence.tcl, POST_FLOORPLAN; OT_FENCE_DENSITY)
# env MARGIN=1 CKINS=<ps> [CKFF=<ps>, FF minimum insertion for the vclk hold latency]: owner margin rule (2026-10-06) -- route against bench/stn_margin_sdc.py route (effective
#     770 ps: setup uncertainty 123 ps, crossing bound -63 ps; ck IO vs vclk at the measured insertion CKINS, 0.2 T +
#     150 ps), then sign off on stn_margin_sdc.py signoff (60 ps, 356.667 ps, same IO): corner STA and the SS/FF ETM
#     export re-run against it (corner_sta.json; the route-SDC STA is kept as corner_sta_route.json).
S=$1; O=$2; lab=$3; m=$4; pd=${5:-0.55}; shift 5
cd $S
V=physical/hbm_accel_die_views/stations/$m/$m.sdc
SDCARG="--orfs-var SDC_FILE=/src/$V"
if [ -n "${MARGIN:-}" ]; then
  mkdir -p $S/.views/$lab
  python3 physical/hbm_accel_die_views/stations/bench/stn_margin_sdc.py $V ${CKINS:-0} route ${CKFF:-} > $S/.views/$lab/route.sdc
  python3 physical/hbm_accel_die_views/stations/bench/stn_margin_sdc.py $V ${CKINS:-0} signoff ${CKFF:-} > $S/.views/$lab/signoff.sdc
  SDCARG="--orfs-var SDC_FILE=/src/.views/$lab/route.sdc"
  mkdir -p $O/$lab
  echo "{\"margin\": true, \"ckins_ps\": ${CKINS:-0}, \"route_sdc\": \".views/$lab/route.sdc\", \"signoff_sdc\": \".views/$lab/signoff.sdc\", \"recipe\": \"bench/stn_margin_sdc.py\"}" > $O/$lab/margin.json
  cp $S/.views/$lab/route.sdc $S/.views/$lab/signoff.sdc $O/$lab/
fi
SRC=$S OUT=$O PD=$pd CORES=${CORES:-6} NEED=${NEED:-12} \
SRCS="rtl/common/ot_fwd_link_stage.sv rtl/common/ot_meso_fifo.sv physical/hbm_accel_die_views/stations/rtl/ot_hbm_stn_lib.sv" \
  physical/hbm_accel_die_views/common/route_view.sh $lab $m physical/hbm_accel_die_views/stations/$m/$m.sv \
  $SDCARG --orfs-var SYNTH_KEEP_MODULES=ot_fwd_clk_inv --step-tcl POST_SYNTH=physical/hbm_accel_die_views/stations/bench/stn_post_synth.tcl --step-tcl PRE_CTS=physical/hbm_accel_die_views/stations/bench/stn_pre_cts.tcl \
  ${FENCE:+--step-tcl POST_FLOORPLAN=physical/hbm_accel_die_views/stations/bench/stn_meso_fence.tcl --step-tcl POST_GLOBAL_PLACE=physical/hbm_accel_die_views/stations/bench/stn_fence_dissolve.tcl --orfs-var OT_IO_FILE=/src/.views/$lab/io_place.tcl} "$@"
if [ -n "${MARGIN:-}" ] && grep -q "^rc=0" $O/$lab/exit; then
  W=$O/$lab; B=$(ls -d $W/work/orfs/results/asap7/*/base); rel=${B#$W/work/orfs/}
  mkdir -p $W/signoff/$rel
  for f in 6_final.odb 6_final.spef; do ln -f $B/$f $W/signoff/$rel/$f 2>/dev/null || cp $B/$f $W/signoff/$rel/$f; done
  cp $S/.views/$lab/signoff.sdc $W/signoff/$rel/6_final.sdc
  [ -f $W/corner_sta.json ] && mv $W/corner_sta.json $W/corner_sta_route.json
  python3 tools/w18/corner_sta.py --orfs-dir $W/signoff --output $W/corner_sta.json > $W/corner_signoff.log 2>&1
  echo "signoff_corner_rc=$?" >> $W/exit
  python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name $m --out $W/view --interface-sdc $S/.views/$lab/signoff.sdc --tmp-dir $W/abs_tmp2 > $W/export_signoff.log 2>&1
  echo "signoff_export_rc=$?" >> $W/exit
fi
