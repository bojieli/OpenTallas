#!/bin/bash
# DIE-QC-20 QC die gate (main tools incl RM165; K/A absolute) (template DIE-QC-18 gate/runGate.sh) on trial $1 arrivals $2 -> $D/$3 ; + measured fall arrivals (tap_fall_merge.py, FLOW-ONEMODEL-1)
set -u
D=/srv/opentallas-scratch2/claude/die-qc20-1028; K=$1; A=$2; R=$D/$3; mkdir -p $R/run
TI=/srv/opentallas-scratch2/claude/wt/die-qc20-1028/tools; MT=/srv/opentallas-scratch2/claude/wt/die-qc20-1028/tools/die_plan
CA=/srv/opentallas-scratch2/claude/die-qc9-1028/ca
MAP=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/part_region.json
PLAN=/srv/opentallas-scratch2/claude/die-qc18-1028/gate/ev_a0meas.json
log(){ echo "g: $1 $(date)" >> $R/chain.log; }
ln -sfn $K/clock $R/run/clk; for C in TT FF; do ln -sfn ${A}_$C $R/run/out_$C; done
python3 -I $TI/s81_head/landed_phase_ocv.py $PLAN $R/run --tools $TI/die_plan --clock-cell inv2 --out $R/lpo.json > $R/lpo.log 2>&1; log "lpo rc $?"
cd $R && PYTHONPATH=$MT python3 $CA/ca_spice.py $R/lpo.json $MAP $R/grp_spice 0.9324 0.9380 --mc 0 > $R/ca.log 2>&1; log "xing rc $?"
python3 -I $CA/mk_proof.py $R/run $MAP $R/proof0 > $R/proof.log 2>&1; log "proof rc $?"
for C in TT FF; do python3 -c "import json,sys; f=sys.argv[1]; d=json.load(open(f)); d[\"clock_cell\"]=\"inv2\"; json.dump(d,open(f,\"w\"))" $R/proof0/tap_arrivals_$C.json; done
mkdir -p $R/proof; cp $R/proof0/droop_regions.json $R/proof0/mesh.json $R/proof/
for C in TT FF; do python3 -I $MT/tap_fall_merge.py $R/proof0 $C ${A}_$C/arr_$C.txt --out $R/pf_$C --tree $K/clock/tree.json > $R/fall_$C.log 2>&1 || { echo TREE-FALLBACK >> $R/fall_$C.log; rm -rf $R/pf_$C; python3 -I $MT/tap_fall_merge.py $R/proof0 $C ${A}_$C/arr_$C.txt --out $R/pf_$C >> $R/fall_$C.log 2>&1; }; cp $R/pf_$C/tap_arrivals_$C.json $R/proof/; done; log "fall merge"
for P0 in proof0 proof; do
PR=$R/$P0
F="--sta-proof $PR --sta-plan $PLAN --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
for M in phase width; do python3 $MT/count_align_plan.py $R/grp_spice_xing_lpo.json $F --start-tree clock --start-clean $M --mc-chips 300 --out $R/plan_${P0}_$M.json > $R/plan_${P0}_$M.log 2>&1 & done; wait; log "plans $P0"
done
PR=$R/proof
F="--sta-proof $PR --sta-plan $PLAN --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
python3 $MT/count_align_bind.py $R/grp_spice_xing_lpo.json --from-ocv --parts ocv --samples 500 $F --start-tree clock --start-clean width --out $R/bind_clock.json > $R/bind_clock.log 2>&1; log "bind rc $?"
python3 $MT/die_sta_related.py $PR --plan $PLAN --out $R/sta_declared --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align $R/bind_clock.json --count-align-key region --core-view qfd_dv_s8x_crh=/srv/opentallas-scratch2/claude/qc/closed/qfd_dv_s8x_crh/kit/views --core-view qfd_dv_s8_crh_rp1=/srv/opentallas-scratch2/claude/autopilot/closed/qwen_compute/qfd_dv_s8_crh_rp1__f4g__5ed4500430/kit/views --clock-cell inv2 --core-insertion declared > $R/sta_declared.log 2>&1; log "sta declared rc $?"; python3 $MT/die_sta_related.py $PR --plan $PLAN --out $R/sta_gate --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align $R/bind_clock.json --count-align-key region --clock-cell inv2 --core-view qfd_dv_s8x_crh=/srv/opentallas-scratch2/claude/qc/closed/qfd_dv_s8x_crh/kit/views --core-view qfd_dv_s8_crh_rp1=/srv/opentallas-scratch2/claude/autopilot/closed/qwen_compute/qfd_dv_s8_crh_rp1__f4g__5ed4500430/kit/views --core-insertion view > $R/sta_gate.log 2>&1; log "sta declared rc $?"
log DONE
