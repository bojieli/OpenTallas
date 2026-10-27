#!/bin/bash
# QC-SU-F4D SIGN-OFF KIT chain (fresh from the plan): F4A MIF0 kit recipe (gen_core_kit_qc config, unchanged RTL/pins/
# floorplan) + F4D plan spec mscts_spec_f4d.tcl (straight legs, 8x8 equal-leaf islands, 12.8 d1 window-only sizing by
# uf_phys3 v1 before build, no entry delay) + tree-net-only M5/M6 guides loaded into the ODB before DRT (pre_drt_f4d.tcl).
#  1 place_m0.sh (the F4A MIF0 synth+floorplan+place recipe) -- from scratch
#  2 placement identity gate vs the F4A MIF0 3_place the plan was computed on (instance name/master/xy/orient); a
#    difference stops the chain (the plan must then be re-gated on the new placement)
#  3 CTS (plan-built, TritonCTS off, ITERS 0) -> GRT (signal M2-M5, clock M4-M5) -> FF-only DATA-path hold repair
#    (hold_grt_f4a.tcl, 12.4a a1; clock fingerprint unchanged) -> DRT with the M5/M6 tree guides -> layer census
#  4 fill/RCX/abstract/pin audit/STA (finish_f4a.sh) -> abstract M6 OBS per shape (abstract_m6.py)
#  5 meas_ck GRT(prehold)+RCX TT/FF -> main signoff.py (+ ft-arc data_arrival_time fix) -> main lec.py on 6_final.v
# No pads/trims/clock ECOs (12.8; no 12.8 d2 residual tool used).  usage: f4d_signoff.sh KITDIR
set -uo pipefail
K=$(cd "$1" && pwd); H=$(cd "$(dirname "$0")" && pwd)
M=$H/main_sofix/tools/die_plan
st() { echo "F4D_STAGE $1 $(date -Is)" | tee -a $K/f4d_chain.txt; }
mk() { local X=${2:-}; docker run --rm --name qcf4d-$1-$(basename $K)-$$ --cpus=16 --memory=40g --memory-swap=40g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 $X $1" > "$K/f4d_$1.log" 2>&1; r=$?; docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work; return $r; }
dpy() { docker run --rm --memory=8g --memory-swap=8g --cpus=2 -v $K:/work -v $2:/s.py:ro $3 openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /s.py' > $1 2>&1; docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work; }
st start
# F4A MIF0 recipe = place_m0.sh (plain ORFS make place, 8 threads, no run_kit preflight); LEC on 6_final.v runs below
bash $K/place_m0.sh > $K/f4d_place.log 2>&1 || { st "place FAIL (see place_m0.log)"; exit 2; }
HB=$(ls -d $K/run/results/asap7/*/base); B=/work/run/results/asap7/$(basename $(dirname $HB))/base
dpy $K/inst_dump.log $H/inst_dump.py "-e ODB=$B/3_place.odb -e OUT=/work/f4d_place.inst"
if cmp -s $K/f4d_place.inst $H/f4a_place_$(cat $K/f4d_type.txt).inst; then st "PLACE_IDENTICAL to F4A MIF0 (plan geometry valid)"; else
  diff $H/f4a_place_$(cat $K/f4d_type.txt).inst $K/f4d_place.inst | head -20 > $K/place_diff.txt; st "PLACE_CHANGED vs F4A: STOP, re-gate the plan on the new placement (place_diff.txt)"; exit 3; fi
mk do-cts || { st "cts FAIL"; exit 4; }
mk do-5_1_grt || { st "grt FAIL"; exit 5; }
grep -h "S5_GRT_TT" $K/s5_grt_tt.txt 2>/dev/null | tail -n 1 >> $K/f4d_chain.txt
cp $HB/5_1_grt.odb $HB/5_1_grt_prehold.odb; cp $HB/route.guide $HB/route_prehold.guide
FF=$(sed -n 's/^export OT_VCLK_FF = //p' $K/config.mk)
docker run --rm --name qcf4d-hold-$(basename $K)-$$ --cpus=16 --memory=24g --memory-swap=24g -v "$K":/work -v $H/hold_grt_f4a.tcl:/h.tcl:ro -w /work \
  -e RESULTS_DIR=$B -e OT_RC_CAL=0.8,0.9 -e OT_VCLK_FF=$FF -e OT_HOLD_MARGIN=15 openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 16 -exit /h.tcl" > $K/hold_f4d.log 2>&1 || { st "hold step FAIL"; exit 6; }
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
cat $K/hold_f4a_gate.txt >> $K/f4d_chain.txt; grep -q "HOLD_F4A_GATE PASS" $K/hold_f4a_gate.txt || { st "hold gate FAIL"; exit 6; }
rm -f $K/run/logs/asap7/*/base/5_2_route.json
mk do-5_2_route || { st "drt FAIL"; exit 7; }
grep -o '"detailedroute__route__drc_errors"[^,]*' $K/run/logs/asap7/*/base/5_2_route.json >> $K/f4d_chain.txt
grep -h "OT_TREE_GUIDE\|GUIDE_M56" $K/f4d_do-5_2_route.log | cut -c1-400 >> $K/f4d_chain.txt
dpy $K/f4d_tree_layers.txt $H/net_layers.py "-e ODB=$B/5_2_route.odb -e NETS=ALL"
dpy $K/f4d_m6_census.txt $H/m6_census.py "-e ODB=$B/5_2_route.odb"
tail -n 1 $K/f4d_m6_census.txt >> $K/f4d_chain.txt
st drt_done
bash $H/finish_f4a.sh $K || { st "finish FAIL"; exit 8; }
TOP=$(sed -n 's/^export DESIGN_NAME = //p' $K/config.mk)
docker run --rm --memory=8g --memory-swap=8g --cpus=2 -v $K:/work -v $H/abstract_m6.tcl:/a.tcl:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; ODB=$B/6_final.odb OUT=$B/${TOP}_pershape.lef openroad -exit -no_splash /a.tcl" > $K/abstract_m6.log 2>&1
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
cp $HB/$TOP.lef $HB/${TOP}_bloated.lef
python3 -I $H/abstract_m6.py $HB/${TOP}_bloated.lef $HB/${TOP}_pershape.lef $HB/$TOP.lef $K/abstract_m6.json >> $K/f4d_chain.txt 2>&1 || st "abstract_m6 FAIL"
bash $H/meas_all.sh $(basename $K) prehold run/results/asap7/$(basename $(dirname $HB))/base >> $K/f4d_chain.txt 2>&1
SIGNOFF_DOCKER=docker python3 -I $M/signoff.py run --run-dir $K/run --kit $K --corners tt,ff --ff-vclk auto --out $K/signoff_main --image openroad/orfs:asap7lock > $K/signoff_main.log 2>&1; so=$?
docker run --rm --memory=24g --memory-swap=24g --cpus=8 -v $K:/work -v $M:/m:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist $B/6_final.v --out /work/lec_final" > $K/lec_final.log 2>&1; lr=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
grep -E '^SIGNOFF' $K/signoff_main.log >> $K/f4d_chain.txt; tail -n 1 $K/lec_final.log >> $K/f4d_chain.txt
st "CHAIN_DONE signoff rc $so lec rc $lr"
exit $so
