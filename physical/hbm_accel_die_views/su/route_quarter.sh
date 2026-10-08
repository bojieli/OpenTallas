#!/bin/bash
# CLAUDE HBM-ABSTRACTS (hub): route one hub quarter envelope view (hfd_su / hfd_sfu / hfd_hc) at its r16g outline and
# die pins with its closed r2 lanes as hard macros, through common/route_view.sh (corner STA, LEF + SS/FF ETM export,
# generator check).  The lane view (LEF + SS/FF lib, committed under <q>/lane/<lane>/) and the macro placement
# (<q>/rtl/macro_place.tcl, tools/hbm_hub_quarter_gen.py --lane-size W H) come from the pinned source snapshot.
# PLACE_DENSITY_LB_ADDON is cleared so PD (route_view.sh --place-density) is the placement target: run_abi3_physical
# always exports LB_ADDON 0.05, which on a quarter that is ~99 % lanes made the target 0.0695 and left global placement
# on an overflow plateau of 0.38 for 1.5 h (q1hc, killed).
#   route_quarter.sh <label> su|sfu|hc [extra run_abi3_physical args]     env: SRC, OUT, PD, CORES, NEED as route_view.sh
set -u
lab=$1; q=$2; shift 2
case $q in su) lane=ot_su12_light;; sfu) lane=ot_su12_sfu;; hc) lane=ot_dsrom_su_hcpost_lane;; esac
V=physical/hbm_accel_die_views/$q
test -f $SRC/$V/lane/$lane/$lane.lef && test -f $SRC/$V/rtl/macro_place.tcl || { echo "missing lane view / placement"; exit 1; }
# the lane is a liberty black box in the route: its parameter overrides (hc: ML 5 / AL 5, fixed in the hardened lane)
# are dropped from the route copy of the wrapper; lint and the bench keep the committed wrapper with them
mkdir -p $SRC/.views/$lab; sed -E 's/ #\(\.[A-Za-z]+\([0-9]+\)(, \.[A-Za-z]+\([0-9]+\))*\) u_lane_/ u_lane_/' $SRC/$V/rtl/hfd_$q.sv > $SRC/.views/$lab/hfd_$q.sv
MACROS="$lane=$V/lane/$lane" PDN=physical/hbm_accel_die_views/su/pdn_quarter.tcl MAXL=M7 \
  bash $SRC/physical/hbm_accel_die_views/common/route_view.sh $lab hfd_$q .views/$lab/hfd_$q.sv \
  --orfs-var MACRO_PLACEMENT_TCL=/src/$V/rtl/macro_place.tcl --orfs-var PLACE_DENSITY_LB_ADDON= --clock-period-ns ${CP:-0.77} --io-delay-fraction 0.4 "$@"
# owner margin rule: routed at CP (default 0.77 ns, passed as --clock-period-ns), signed off at 833 ps
cd $SRC && python3 tools/w18/corner_sta.py --macro $V/lane/$lane --orfs-dir $OUT/$lab/work/orfs \
  --post-sdc physical/hbm_accel_die_views/su/signoff833_ck.sdc --output $OUT/$lab/corner_sta_833.json > $OUT/$lab/corner833.log 2>&1
echo "signoff833_rc=$?" >> $OUT/$lab/exit
