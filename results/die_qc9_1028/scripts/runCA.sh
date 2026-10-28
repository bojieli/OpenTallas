#!/bin/bash
# DIE-QC-9: CA + die STA chain on a trial (CA-OCV-1 tools merged on claude/die-qc9-1028): lpo (legacy + --port-taps) ->
# ca_spice xing (spice x1.0485/x1.0552, region crossings) -> proof (mk_proof) -> count_align_bind --from-ocv with the
# --sta-proof hull + CA-OCV-1 --sta-clock-ocv table --sta-clock-droop shared -> main die_sta_related (spice, region key,
# cppr-lca, table/shared, HB none/HB4).  usage: runCA.sh TRIAL TAG [--port-taps]
set -u
Q=/srv/opentallas-scratch2/claude/die-qc9-1028; TR=$1; R=$Q/ca/$2; PT=${3:-}
T=/srv/opentallas-scratch2/claude/wt/die-qc9-1028/tools
CI=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs
PLAN=$CI/event/qc_k2b_phase12.json; MAP=$CI/part_region.json
TP="${TREE_PARENT:-}"
log(){ echo "$2: $1 $(date)" >> $R/chain.log; }
mkdir -p $R/run; ln -sfn $Q/$TR/clock $R/run/clk
for C in TT FF; do ln -sfn $Q/c${TR#trial}_$C $R/run/out_$C; done
python3 -I $T/s81_head/landed_phase_ocv.py $PLAN $R/run --tools $T/die_plan $PT --out $R/lpo.json > $R/lpo.log 2>&1; log "lpo rc $?" $2
cd $R && PYTHONPATH=$T/die_plan python3 $Q/ca/ca_spice.py $R/lpo.json $MAP $R/grp_spice 1.0485 1.0552 --mc 0 > $R/ca.log 2>&1; log "xing rc $?" $2
python3 -I $Q/ca/mk_proof.py $R/run $MAP $R/proof > $R/proof.log 2>&1; log "proof rc $?" $2
X=$R/grp_spice_xing_lpo.json
STA="--sta-proof $R/proof --sta-plan $PLAN --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $R/proof/droop_regions.json --sta-core-latency-ff 202.5"
STA0="--sta-proof $R/proof --sta-plan $PLAN --sta-clock-cal spice --sta-cppr-lca --sta-core-latency-ff 202.5"
python3 $T/die_plan/count_align_plan.py $X $TP $STA --out $R/plan.json > $R/plan.log 2>&1; log "plan (CA-OCV-1 table/shared) rc $?" $2
python3 $T/die_plan/count_align_plan.py $X $TP $STA0 --out $R/plan_noocv.json > $R/plan_noocv.log 2>&1; log "plan (no clock-variation term, INFO) rc $?" $2
python3 $T/die_plan/count_align_bind.py $X --from-ocv --parts ocv --samples 2000 $TP $STA --out $R/bind.json > $R/bind.log 2>&1; log "bind rc $?" $2
if [ ! -s $R/bind.json ]; then   # INFO bind: plan-FAIL crossings dropped (never a gate number)
  python3 -I $Q/ca/info_drop.py $X $R/plan.json $R/xing_INFO.json >> $R/bind.log 2>&1
  python3 $T/die_plan/count_align_bind.py $R/xing_INFO.json --from-ocv --parts ocv --samples 2000 $TP $STA --out $R/bind.json >> $R/bind.log 2>&1; log "bind INFO (plan FAIL dropped) rc $?" $2
fi
for HB in none HB4; do
  python3 $T/die_plan/die_sta_related.py $R/proof --plan $PLAN --out $R/sta_$HB --corner TT --corner FF --core-latency-ff 202.5 --clock-ocv table --clock-droop shared --droop-regions $R/proof/droop_regions.json --hold-buffers $HB --cppr-lca --clock-cal spice --count-align $R/bind.json --count-align-key region > $R/sta_$HB.log 2>&1; log "sta $HB rc $?" $2 &
done; wait; log DONE $2
