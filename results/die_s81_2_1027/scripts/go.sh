#!/bin/bash
# DIE-S81-2: 98-region map plan event (count-aligned) -> compose landings -> latency -> G0/G0C -> spine_fishbone kit (250 um reps)
# -> model margins -> die GRT incl clock TT+FF (50 it) -> landed_phase_ocv -> count_align_plan (CA margins) -> renders
set -u
WT=/srv/opentallas-scratch2/claude/wt/die-s81-2; O=/srv/opentallas-scratch2/claude/die-s81-2; PD=$WT/physical/die_plan/s81
R=$WT/results/die_s81_2_1027; J=$PD/die_plan_r98.json
cd $WT; ulimit -v 60000000
echo START $(date) host $(hostname) code $(git rev-parse --short HEAD)
python3 tools/die_plan/fallback_regions.py plan $PD/die_plan.json --lat $PD/lat/s81_latency.json --out $O/reg --block 2 --mode class --core tap --groups $R/groups98.json > $O/reg.log 2>&1; echo REG $? $(date); head -c 600 $O/reg.log; echo
python3 results/land_s81_1027/scripts/compose_plan.py $PD/die_plan.json $O/reg/landed_crossings.json $J $O/side.json > $O/compose.log 2>&1; echo COMPOSE $? $(date); tail -1 $O/compose.log | cut -c1-600
python3 tools/die_plan/gen.py latency $J --inplace --out $O/gen_lat > $O/gen_lat.log 2>&1; echo LAT $? $(date)
( python3 tools/die_plan/check.py $J --completeness --out $O/g0c > $O/g0c.log 2>&1; echo G0C_DONE $(date); tail -3 $O/g0c.log ) &
python3 tools/die_plan/die_trial.py kit $J --out $O/kit --tree-form spine_fishbone --rep-um 250 --tree-site-slide > $O/kit.log 2>&1; echo KIT $? $(date); tail -3 $O/kit.log
python3 tools/die_plan/die_trial.py render $O/kit --plan $J > $O/render.log 2>&1 || echo RENDER_FAIL
python3 tools/s81_head/landed_topo_model.py $J $O/kit/clock $O/model --tools $WT/tools/die_plan > $O/model.log 2>&1; echo MODEL $? $(date); tail -4 $O/model.log | cut -c1-300
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for C in TT FF; do
  CORNER=$C ADJ=0.75 python3 $WT/results/land_s81_1027/scripts/mk_combo_dcm.py $O/kit $O/clk $O/out_$C > $O/mk_$C.log 2>&1 || { echo MK_FAIL $C; tail $O/mk_$C.log; exit 1; }
  docker run -d --name dies81-2-$C --memory=56g --memory-swap=56g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v $O/kit:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait dies81-2-$C; docker rm dies81-2-$C >/dev/null; done
echo COMBO_DONE $(date)
for C in TT FF; do grep -E "^(M[1-9]|Total) " $O/out_$C/combo_$C.log | tail -10; echo "GRT-0113/4 $(grep -c 'GRT-011[34]' $O/out_$C/combo_$C.log)"; tail -2 $O/out_$C/combo_$C.log; done
python3 tools/s81_head/landed_phase_ocv.py $J $O --tools $WT/tools/die_plan --out $O/landed_ocv.json > $O/landed_ocv.log 2>&1; cut -c1-260 $O/landed_ocv.log
python3 tools/die_plan/count_align_plan.py $O/landed_ocv.json --out $O/ca_plan.json > $O/ca_plan.log 2>&1; echo CA $? ; head -40 $O/ca_plan.log
python3 tools/s81_head/fallback_land_report.py $J $O --png $O/landed.png > $O/report.log 2>&1; tail -5 $O/report.log
wait
echo END $(date)
