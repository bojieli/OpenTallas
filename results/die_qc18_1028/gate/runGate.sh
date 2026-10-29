#!/bin/bash
# DIE-QC-18 (COORD 14:xx ruling): QC die gate on the MEASURED A0 trunks (nk t5 / nl b5 median routed insertion).
# Proof = DIE-QC-16 trial12 (c_* A0 early taps, clock GRT TT/FF). Template = DIE-QC-13 ca/runCA11i.sh.
# Tools: CA + die STA = origin/main 4460e18d64 (shared model); landed_phase_ocv --clock-cell inv2 = DIE-QC-13 invcal
# PREVIEW (CLK-INV-CAL-1 rework RM165 not on main) -> every result here is PREVIEW / DECLARED, never a gate PASS.
set -u
G=/srv/opentallas-scratch2/claude/die-qc18-1028/gate; Q=/srv/opentallas-scratch2/claude/die-qc16-1028
R=$G/t12m; mkdir -p $R/run
TI=/srv/opentallas-scratch2/claude/die-qc13-1028/invcal/tools; MT=$G/tm/tools/die_plan
CA=/srv/opentallas-scratch2/claude/die-qc9-1028/ca
MAP=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/part_region.json
PLAN=$G/ev_a0meas.json
log(){ echo "g: $1 $(date)" >> $R/chain.log; }
ln -sfn $Q/trial12/clock $R/run/clk; for C in TT FF; do ln -sfn $Q/c12_$C $R/run/out_$C; done
python3 -I $TI/s81_head/landed_phase_ocv.py $PLAN $R/run --tools $TI/die_plan --clock-cell inv2 --out $R/lpo.json > $R/lpo.log 2>&1; log "lpo rc $?"
cd $R && PYTHONPATH=$MT python3 $CA/ca_spice.py $R/lpo.json $MAP $R/grp_spice 0.9324 0.9380 --mc 0 > $R/ca.log 2>&1; log "xing rc $?"
python3 -I $CA/mk_proof.py $R/run $MAP $R/proof > $R/proof.log 2>&1; log "proof rc $?"
for C in TT FF; do python3 -c "import json,sys; f=sys.argv[1]; d=json.load(open(f)); d[\"clock_cell\"]=\"inv2\"; json.dump(d,open(f,\"w\"))" $R/proof/tap_arrivals_$C.json; done
PR=$R/proof
F="--sta-proof $PR --sta-plan $PLAN --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
for M in phase width; do python3 $MT/count_align_plan.py $R/grp_spice_xing_lpo.json $F --start-tree clock --start-clean $M --mc-chips 300 --out $R/plan_$M.json > $R/plan_$M.log 2>&1; log "plan $M rc $?"; done
python3 $MT/count_align_bind.py $R/grp_spice_xing_lpo.json --from-ocv --parts ocv --samples 500 $F --start-tree clock --start-clean width --out $R/bind_clock.json > $R/bind_clock.log 2>&1; log "bind rc $?"
for CI in declared view; do
python3 $MT/die_sta_related.py $PR --plan $PLAN --out $R/sta_$CI --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align $R/bind_clock.json --count-align-key region --core-view qfd_dv_s8x_crh=/srv/opentallas-scratch2/claude/qc/closed/qfd_dv_s8x_crh/kit/views --core-view qfd_dv_s8_crh_rp1=/srv/opentallas-scratch2/claude/autopilot/closed/qwen_compute/qfd_dv_s8_crh_rp1__f4g__5ed4500430/kit/views --core-insertion $CI > $R/sta_$CI.log 2>&1; log "sta $CI rc $?"
done
log DONE
