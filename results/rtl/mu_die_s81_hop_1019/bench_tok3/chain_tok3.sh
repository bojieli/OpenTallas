#!/bin/bash
# LEAD2-S81/TOK3: wait for the ot-run client, copy run dirs back (no obj/trace), consumer checks (epcheck) all/hop + mutants.
H=/home/ubuntu/scratch/s81-tok3; WT=/home/ubuntu/wt/s81-tok3-1019; R=/srv/opentallas-scratch/claude/s81-tok3; P=$1
while kill -0 $P 2>/dev/null; do sleep 120; done
mkdir -p $H/runs; for o in out_base out_base_tagdrop out_base_wrongcopy out_rtl_tagdrop; do
  timeout 1200 rsync -a --exclude obj --exclude trace.txt -e "ssh -o ControlPath=none" ot-epyc7:$R/$o ot-epyc7:$R/$o.client.log $H/runs/; done
cd $WT || exit 1
ec() { o=$1; r=$2; s=$3; shift 3; timeout 900 python3 tools/s81_dv/dv_cut_replay.py epcheck --replay $H/R/$r --run $H/runs/$o --scope $s \
  --out $H/runs/epcheck_${s}_$o.json "$@" > $H/runs/epcheck_${s}_$o.log 2>&1; echo "$(date +%H:%M) $o $s $* rc $? | $(tail -n1 $H/runs/epcheck_${s}_$o.log | cut -c1-200)"; }
ec out_base R_cut_7_L0_hop012 all; ec out_base R_cut_7_L0_hop012 hop
ec out_base_tagdrop R_cut_7_L0_hop012_tagdrop hop --expect-fail; ec out_base_wrongcopy R_cut_7_L0_hop012_wrongcopy hop --expect-fail
ec out_rtl_tagdrop R_cut_7_L0_hop012 hop --expect-fail
echo CHAIN_DONE
