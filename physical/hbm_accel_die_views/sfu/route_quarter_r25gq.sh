#!/bin/bash
# [sfu] hbm-phys-1010 2026-10-10: route the FOLDED tiled hfd_sfu quarter (R25GQ slot 2016.144 x 1095.12: 16 hfd_sfu_tile
# hard macros, 2 chains x 8 in 6 column segments of 3, a relay each way at every turn) through common/route_view.sh, then
# the 833-ps corner signoff.  Pins: the r25gqn die-view port record committed in rtl_tiled_r25gq (PORTSDIR; fp decision
# (a): no lgW pass-through, the narrow W-face client tap f_lgW / t_lgW, the HGI client ports and ck0-7 on E).  Every die
# pin lands on a face-chain flop at the pin (generator face_stages, <= 480 um a hop, FCP / FCF place them); the tile
# chains are registered links (tile pins are register pins).
#   route_quarter_r25gq.sh <label> [extra run_abi3_physical args]
#   env: SRC, OUT, PD, CORES, NEED, HM, CP; TILEVIEW (the closed hfd_sfu_tile view dir)
set -u
lab=$1; shift
V=physical/hbm_accel_die_views/sfu
R=${RTL:-$V/rtl_tiled_r25gq}
test -f $SRC/${TILEVIEW:?}/hfd_sfu_tile.lef && test -f $SRC/$R/macro_place.tcl || { echo "missing tile view / placement"; exit 1; }
CKP="ck*" PORTSDIR=$R FCP=1 FCF=$R/face_stages.tcl \
  MACROS="hfd_sfu_tile=$TILEVIEW" PDN=${PDNQ:-physical/hbm_accel_die_views/su/pdn_quarter.tcl} MAXL=M7 \
  bash $SRC/physical/hbm_accel_die_views/common/route_view.sh $lab hfd_sfu $R/hfd_sfu.sv \
  --orfs-var MACRO_PLACEMENT_TCL=/src/$R/macro_place.tcl --orfs-var PLACE_DENSITY_LB_ADDON= --clock-period-ns ${CP:-0.77} --io-delay-fraction 0.4 "$@"
cd $SRC && python3 tools/w18/corner_sta.py --macro $TILEVIEW --orfs-dir $OUT/$lab/work/orfs \
  --post-sdc $V/signoff833_ck8.sdc --output $OUT/$lab/corner_sta_833.json > $OUT/$lab/corner833.log 2>&1
echo "signoff833_rc=$?" >> $OUT/$lab/exit
