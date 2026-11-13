#!/bin/bash
# HEAD-97 rp21x wave-PREPARED tree + kit_rtl export + gen (recipe = KIT-OPS-1, as prep20a/gen20b), tools = private tree
# wt/head-97-rp20 (main + REACH-TOOL-3 + head-97-xohop + train 61 rules-flow-1)
set -u; cd /
H=/srv/opentallas-scratch2/claude/head-97; D=/srv/opentallas-scratch2/claude/wt/head-97-rp20; W=${PW:-$H/prep21}; O=${PO:-$H/kits21}
P=physical/die_plan/s81_head/plan_of_record; MESH=$D/$P/l48hp1_head_mesh_1111
TYPES="${PT:-hd_tile hd_mesh hd_host_e hd_host_w hd_spn_end hd_spn_eshim_tx hd_st_n3_transit hd_st_str hd_turn_a}"
[ -e $W ] && { echo EXISTS; exit 3; }
mkdir -p $W/compose $W/tmp $O; export TMPDIR=$W/tmp
cp $H/pd/rp21x.json $W/compose/source_plan.json
echo "rp21x plan sha $(sha256sum $W/compose/source_plan.json | cut -c1-16)"
python3 -I $MESH/prepare_cut.py $D $W/compose $H/base/hp1 $W/prep > $W/prepare.log 2>&1; echo "prepare rc $?"; tail -2 $W/prepare.log
for f in core_pins assets native_domains lat; do cp -rL --update=none $H/pd/$f/. $W/prep/$f/; done
for f in core_conns.json core_conns_from_netlist.receipt.json raw_exports.json asbuilt_pricing.json; do [ -e $W/prep/$f ] || cp -L $H/pd/$f $W/prep/; done
[ -e $W/prep/inputs ] || cp -rL $H/pd/inputs $W/prep/inputs
python3 -I $D/$P/l48hp1_head_freg_1111/apply_sidecar.py $W/prep $H/pd/sidecar_rp21.json > $W/sidecar.log 2>&1; echo "sidecar rc $?"; tail -1 $W/sidecar.log
(cd $D && nice python3 -I $MESH/republish.py $D $W/prep ${TYPES// /,} > $W/republish.log 2>&1; echo "republish rc $?"); tail -2 $W/republish.log
sha256sum $W/prep/source_plan.json $W/prep/source_sidecar.json $W/prep/wave_prepare.json | cut -c1-24
mkdir -p $W/x
for t in $TYPES; do
  (cd $D && TYPE=$t OUT=$W/x/$t PLAN=$W/prep/source_plan.json nice -n 19 bash $P/../kit_wave/kit_rtl.sh > $W/x/$t.log 2>&1; echo "KITRTL $t rc $? $(tail -1 $W/x/$t.log | cut -c1-140)") &
done; wait
envof() { case $1 in
  hd_tile) echo "OT_IO_HOLD=sender_min OT_CORE_OUT_LAND=1 OT_GEN_M8_GRANT=1";;
  hd_host_w|hd_host_e) echo "OT_GEN_M8_GRANT=1";;
  *) echo "OT_IO_HOLD=sender_min OT_GEN_M8_GRANT=1";; esac; }
for t in $TYPES; do
  [ -f $W/x/$t/kit_rtl.f ] || { echo "GEN $t SKIP no kit_rtl.f"; continue; }
  (cd $D && env $(envof $t) python3 -I tools/die_plan/gen.py phys $W/prep/source_plan.json \
     --clock-landing $W/prep/source_sidecar.json --hold-ff-margin 0 --types $t --kit-rtl $t=$W/x/$t/kit_rtl.f \
     --out $O/g_$t --rtl-root $D > $O/gen_$t.log 2>&1; echo "GEN $t rc $? $(tail -1 $O/gen_$t.log | cut -c1-140)") &
done
wait; echo PREP21_DONE
