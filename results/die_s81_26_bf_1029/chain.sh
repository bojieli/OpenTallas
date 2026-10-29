#!/bin/bash
# DIE-S81-26 BF TAG16 core clock re-plan + kit regen + PLACE, one variant: chain.sh t16a|t16b
# census (placed trial census kit, own netlist) -> form C planner (codex-icg-tree-1028 src, same code/family as the d25 plan,
# entry = current kit pin) -> converter (band/window INFO, 12.3a) -> master_slice.kit_apply -> exact sink check vs 1_synth.v
# -> enable-isolation repack (Codex pack logic) on the new slice -> GOAL=place
set -uo pipefail
V=$1; B=/srv/opentallas-scratch2/claude/die-s81-26/bf; CK=$B/kits/cen_$V; KV=$B/kits/bf_$V; P=$B/planner; W=$B/plan_$V; S=$P/src/tools/die_plan
M=$B/main_tools/tools/die_plan; IMG=openroad/orfs:asap7lock; NICK=kl_ot_v41_bf_col_ds81_25_$V; ST=$B/chain_$V.status
log(){ echo "$1 $(date -Is)" >> $ST; }
fail(){ log "FAIL $1"; exit 1; }
log start
ODB=$CK/run/results/asap7/$NICK/base/3_place.odb
[ -f $ODB ] || fail "no census 3_place.odb (census place unit not done/failed)"
mkdir -p $W/ot_v41_bf_col $W/slice
D="docker run --rm --memory=8g --memory-swap=8g -v $CK:/work -v $S:/tcl:ro"
OR="source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit"
$D -e ODB=/work/run/results/asap7/$NICK/base/3_place.odb -e OUT=/work/r13_geo_gated.txt -e CLK=clk -e GATED=1 -e "ENTRY=273.228 95.58" $IMG bash -lc "$OR /tcl/core_family_geo.tcl" > $W/ot_v41_bf_col/geo_gated.log 2>&1 || fail geo_gated
$D -e ODB=/work/run/results/asap7/$NICK/base/3_place.odb -e OUT=/work/r13_geo.txt -e CLK=clk -e "ENTRY=273.228 95.58" $IMG bash -lc "$OR /tcl/core_family_geo.tcl" > $W/ot_v41_bf_col/geo.log 2>&1 || fail geo
$D -e ODB=/work/run/results/asap7/$NICK/base/2_floorplan.odb -e OUT=/work/r13_sites.txt $IMG bash -lc "$OR /tcl/core_family_sites.tcl" > $W/ot_v41_bf_col/sites.log 2>&1 || fail sites
mv $CK/r13_geo_gated.txt $W/ot_v41_bf_col/geo_gated.txt; mv $CK/r13_geo.txt $W/ot_v41_bf_col/geo.txt; mv $CK/r13_sites.txt $W/ot_v41_bf_col/sites.txt
grep -o "^DUMP_GEO_CLKPORT .*" $W/ot_v41_bf_col/geo.log | awk "{print \$2}" > $W/ot_v41_bf_col/clkport.txt
log "census sinks $(grep -c ^SINK $W/ot_v41_bf_col/geo_gated.txt) gates $(grep -c ^GATE $W/ot_v41_bf_col/geo_gated.txt) pin $(grep "^PIN" $W/ot_v41_bf_col/geo_gated.txt)"
cd $P
python3 src/tools/die_plan/core_family_slice.py run --family $B/fam26.json --core ot_v41_bf_col --kit $CK --work $W --libtt lib/invbuf_tt.lib --libff lib/invbuf_ff.lib --fit src/results/model_refit3_1026/uf_phys3_v1.json --libdir lib --seqtt lib/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib --seqff lib/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib > $W/plan.log 2>&1
log "planner rc $? $(grep -o "CORE_FAMILY_SLICE.*" $W/plan.log | cut -c1-300)"
PJ=$W/ot_v41_bf_col/plan_d1.json; [ -f $PJ ] || fail "no plan_d1.json"
python3 $M/core_plan_to_infra.py $PJ --sites $W/ot_v41_bf_col/sites.txt --module ot_v41_bf_col --clock-port clk --band info --window-policy info --ndr none --out $W/slice/ot_v41_bf_col.json > $W/convert_info.log 2>&1 || fail convert
mkdir -p $KV/d25_slice_backup; for f in master_slice.json master_slice.tcl master_core_infra.tcl core_infra_plan.json core_infra_impl.tcl io.tcl bf_enable_isolation.tsv core_infra_cts.tcl; do [ -f $KV/$f ] && cp -p $KV/$f $KV/d25_slice_backup/; done
rm -f $KV/core_infra_post.v
python3 $B/apply26.py $M $KV $W/slice > $W/kit_apply.log 2>&1 || fail kit_apply
grep -n "place_pin -pin_name {clk}" $KV/io.tcl >> $W/kit_apply.log
python3 $B/sinkcheck.py $KV/master_slice.json $KV/run/results/asap7/$NICK/base/1_synth.v $B/tools > $W/sinkcheck.json 2>&1 || fail "sinkcheck (see $W/sinkcheck.json)"
log "sinkcheck PASS $(python3 $B/apply26.py --summary $W/sinkcheck.json)"
rm -f $KV/bf_enable_isolation.tsv
docker run --rm --memory=8g --memory-swap=8g -v $KV:/work -v $CK:/cen:ro -v $B:/b:ro -v $S:/tcl:ro -e V=$V -e RESULTS_DIR=/tmp $IMG bash -lc "$OR /b/pass1.tcl && ODB=/work/pass1.odb OUT=/work/enable_sites.txt openroad -exit /tcl/core_family_sites.tcl" > $W/pass1.log 2>&1 || fail pass1
cd $M && python3 $B/pack26.py $KV/master_slice.json $KV/enable_sites.txt $W/enable_isolation.json $KV/bf_enable_isolation.tsv > $W/pack.log 2>&1 || fail pack
rm -f $KV/pass1.odb $KV/core_infra_post.v
log "pack $(tail -1 $W/pack.log | cut -c1-300)"
echo "DIE-S81-26 10-29: core clock plan rebuilt from the TAG16 census ($W), slice re-applied, enable isolation repacked. Scope synth..PLACE diagnostic only; no DRT/SIGNED." >> $KV/DIAGNOSTIC_ONLY.txt
bash $KV/run_kit.sh $KV place 16 8; rc=$?
log "place rc $rc"
