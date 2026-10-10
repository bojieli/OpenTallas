#!/bin/bash
# [su] hbm-phys-1010: route the TILED hfd_su quarter (R25GQ: 128 hfd_su_tile_xl hard macros, 8 columns x 16 chains,
# 2016.144 x 2808 um) through common/route_view.sh, then the 833-ps corner signoff.  The die pins are the committed port
# contract PORTSDIR (su/r25gq_contract: R25GPHT4 ports on the R25GQ faces, provisional until the R25GQ die net build);
# every die pin lands on a face-chain flop at the pin (generator face_stages, <= 480 um a hop, FCP/FCF places them),
# the tile chains are credit-free registered links (tile pins are register pins, generator check).
#   route_quarter_tiled.sh <label> [extra run_abi3_physical args]
#   env: SRC, OUT, PD, CORES, NEED, HM, CP; RTL (default su/rtl_tiled_xl_r25gq), TILEVIEW (the closed tile_xl view dir)
set -u
lab=$1; shift
V=physical/hbm_accel_die_views/su
R=${RTL:-$V/rtl_tiled_xl_r25gq}
test -f $SRC/${TILEVIEW:?}/hfd_su_tile_xl.lef && test -f $SRC/$R/macro_place.tcl || { echo "missing tile view / placement"; exit 1; }
CKP="ck*" PORTSDIR=${PORTSDIR:-$V/r25gq_contract} FCP=1 FCF=$R/face_stages.tcl \
  MACROS="hfd_su_tile_xl=$TILEVIEW" PDN=${PDNQ:-$V/pdn_quarter.tcl} MAXL=M7 \
  bash $SRC/physical/hbm_accel_die_views/common/route_view.sh $lab hfd_su $R/hfd_su.sv \
  --orfs-var MACRO_PLACEMENT_TCL=/src/$R/macro_place.tcl --orfs-var PLACE_DENSITY_LB_ADDON= --clock-period-ns ${CP:-0.77} --io-delay-fraction 0.4 "$@"
cd $SRC && python3 tools/w18/corner_sta.py --macro $TILEVIEW --orfs-dir $OUT/$lab/work/orfs \
  --post-sdc $V/signoff833_ck8.sdc --output $OUT/$lab/corner_sta_833.json > $OUT/$lab/corner833.log 2>&1
echo "signoff833_rc=$?" >> $OUT/$lab/exit
