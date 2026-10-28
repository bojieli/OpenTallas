#!/bin/bash
# CLK-INV-CAL-1: QC trial9 / trial10 built-arrival CA with the inverter-calibrated shared model (branch tools; auto clock
# cell = inv from run/clk/ctree.v). Same chain as DIE-QC-11 runCA9/10.sh; ca_spice factors = SPICE_CLOCK_CAL_INV.
set -u
TR=$1; FT=$2; FF=$3
M=/srv/opentallas-scratch2/claude/clk-inv-cal-1-1028; Q=/srv/opentallas-scratch2/claude/die-qc11-1028; Q9=/srv/opentallas-scratch2/claude/die-qc9-1028
T=/srv/opentallas-scratch2/claude/wt/clk-inv-cal-1/tools; MT=$T/die_plan
CI=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs; PLAN=$CI/event/qc_k2b_phase12.json; MAP=$CI/part_region.json
R=$M/qc/$TR; mkdir -p $R/run; S=$Q/ca/$TR
log(){ echo "$TR: $1 $(date)" >> $R/chain.log; }
ln -sfn $(readlink $S/run/clk) $R/run/clk; for C in TT FF; do ln -sfn $(readlink $S/run/out_$C) $R/run/out_$C; done
python3 -I $T/s81_head/landed_phase_ocv.py $PLAN $R/run --tools $T/die_plan --out $R/lpo.json > $R/lpo.log 2>&1; log "lpo rc $?"
cd $R && PYTHONPATH=$T/die_plan python3 $Q9/ca/ca_spice.py $R/lpo.json $MAP $R/grp_spice $FT $FF --mc 0 > $R/ca.log 2>&1; log "xing rc $?"
python3 -I $Q9/ca/mk_proof.py $R/run $MAP $R/proof > $R/proof.log 2>&1; log "proof rc $?"
PR=$R/proof
F="--sta-proof $PR --sta-plan $PLAN --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
python3 $MT/count_align_plan.py $R/grp_spice_xing_lpo.json $F --start-tree clock --start-clean phase --mc-chips 300 --out $R/plan_phase.json > $R/plan_phase.log 2>&1; log "plan phase rc $?"
python3 $MT/count_align_bind.py $R/grp_spice_xing_lpo.json --from-ocv --parts ocv --samples 500 $F --start-tree clock --out $R/bind_clock.json > $R/bind_clock.log 2>&1; log "bind rc $?"
python3 $MT/die_sta_related.py $PR --plan $PLAN --out $R/sta_clock --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align $R/bind_clock.json --count-align-key region > $R/sta_clock.log 2>&1; log "sta rc $?"
log DONE
