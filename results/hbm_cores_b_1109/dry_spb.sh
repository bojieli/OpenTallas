#!/usr/bin/env bash
# HBM-SPB-IO: GEN dry per type (pattern of DIE-HBM-93 dry_full.sh), plan_spbio + vJ bind, DIE-HBM-93 src read-only.
set -u
R=/srv/opentallas-scratch3/claude/hbm-spb-io
S=/srv/opentallas-scratch2/claude/die-hbm-93/src_full
P=${P:-/srv/opentallas-scratch2/claude/hbm-spb-io/plan_spbio/die_plan.json}
A=/srv/opentallas-scratch3/claude/die-hbm-93/lat/asbuilt_p37su5_sm_lat_vJ.json
B=/srv/opentallas-scratch3/claude/die-hbm-93/lat/bind_lat_vJ
D=$R/dry
mkdir -p $D
export PYTHONDONTWRITEBYTECODE=1 OT_FLOW_TAG=flow-20261108-fn-hbm R S P A B D
one() {
 T=$1; O=$D/$T; rm -rf $O; mkdir -p $O; cd $S
 st() { echo "$1 $2" >> $O/rc.txt; }
 python3 tools/die_plan/bind.py kit-rtl $P --out $B --asbuilt $A --type $T --kit $O/rtl > $O/kit_rtl.log 2>&1; r=$?; st KITRTL $r; [ $r = 0 ] || return
 mkdir -p $O/prov/routed
 python3 -I tools/autopilot/prov_view.py make --plan $P --type $T --out $O/prov --src $S --routed $O/prov/routed --rtl $O/rtl > $O/prov.log 2>&1; r=$?; st PROV $r; [ $r = 0 ] || return
 OV=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1]))[\"overlay_plan\"])" $O/prov/provisional_views.json)
 python3 -I tools/die_plan/kit_topology.py prepare-stations $OV $T $O/rtl --native-plan $P --asbuilt $A > $O/topology.log 2>&1; r=$?; st TOPO $r; [ $r = 0 ] || return
 nice prlimit --as=24000000000 python3 tools/die_plan/gen.py phys $OV --out $O/gen --types $T --rtl-root $S --kit-rtl $T=$O/rtl/kit_rtl.f --cland-pinslot all > $O/gen.log 2>&1; r=$?; st GEN $r; [ $r = 0 ] || return
 python3 tools/die_plan/kit_gen_lint.py $O/gen/$T --plan-dir $(dirname $OV) --mem 8 > $O/gen_lint.log 2>&1; r=$?; st GEN_LINT $r; [ $r = 0 ] || return
 python3 tools/die_plan/kit_preflight.py $O/gen/$T --plan-dir $(dirname $OV) --contract --out $O/preflight.json > $O/preflight.log 2>&1; r=$?; st PREFLIGHT $r
}
export -f one
echo ${TYPES:-q_spb0 NE_io vsN0 q_spb0__physical_v1 NW_io} | tr " " "\n" | xargs -P 5 -I{} bash -c "one {}"
for t in ${TYPES:-q_spb0 NE_io vsN0 q_spb0__physical_v1 NW_io}; do echo "$t $(tr "\n" " " < $D/$t/rc.txt)"; done > $D/summary.txt
echo DONE > $D/done
