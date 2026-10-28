#!/bin/bash
# DIE-S81-15: go14 post (render, --cell-paths proof, die STA declared + view(fail-closed), CA width cell-paths / phase)
set -u
W=/srv/opentallas-scratch2/claude/wt/die-s81-15; MT=$W/tools/die_plan; O=/srv/opentallas-scratch2/claude/die-s81-15/cp14
G=/srv/opentallas-scratch2/claude/die-s81-14/go14; PL=/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json
echo START $(date) code $(git -C $W rev-parse --short HEAD)
python3 $O/ctree_pil.py $G/clk/tree.json $PL $O/ctree14.png
mkdir -p $O/clkcp; ln -sfn $G/clk/ctree.v $O/clkcp/ctree.v
python3 /srv/opentallas-scratch2/claude/die-s81-15/physpath.py $G/clk/tree.json $O/clkcp/tree.json
mkdir -p $O/proof; cp $G/proof/{mesh,droop_regions}.json $O/proof/
for C in TT FF; do python3 $MT/trial_tap_arrivals.py $O/clkcp/tree.json $G/out_$C/arr_$C.txt $C $O/proof/tap_arrivals_$C.json; done
# lpo (landed phase rows) on the go14 proof, as go13 (DIE-S81-13 lpo recipe)
python3 -c "import json;print(clock_cell, json.load(open(/proof/tap_arrivals_TT.json)).get(clock_cell))"
mkdir -p $O/lpo; ln -sfn $G/clk $O/lpo/clk; ln -sfn $G/out_TT $O/lpo/out_TT; ln -sfn $G/out_FF $O/lpo/out_FF
python3 $W/tools/s81_head/landed_phase_ocv.py $PL $O/lpo --tools $MT --out $O/lpo.json > $O/lpo.log 2>&1; echo "LPO_RC $?"
for M in declared view; do
python3 $MT/die_sta_related.py $O/proof --plan $PL --out $O/sta_$M --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $O/proof/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --clock-cell inv2 --core-insertion $M > $O/sta_$M.log 2>&1; echo "sta $M rc $?"; grep -E "intra |core.insertion|missing" $O/sta_$M.log | cut -c1-300 | head -6; done
PR=$O/proof; X=$O/lpo.json
F="--sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5 --sta-clock-cell inv2"
for M in width phase; do
  B=$O/ca_$M; mkdir -p $B; UP=""; [ $M = width ] && UP="--start-retime-up --start-retime-max 8"
  python3 $MT/count_align_plan.py $X $F --start-tree clock --start-clean $M $UP --mc-chips 300 --out $B/plan.json > $B/plan.log 2>&1; echo "plan $M rc $?"
  python3 $MT/count_align_bind.py $X --from-ocv --parts ocv --scale 1.0 --samples 2000 $F --start-tree clock --start-clean $M $UP --out $B/bind.json > $B/bind.log 2>&1; echo "bind $M rc $?"
  [ -f $B/bind.json ] && { python3 $MT/die_sta_related.py $PR --plan $PL --out $B/sta --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --clock-cell inv2 --core-insertion declared --count-align $B/bind.json --count-align-key region > $B/sta.log 2>&1; echo "sta $M rc $?"; grep -E "COUNT-ALIGN|START" $B/sta.log | cut -c1-300; }
done
echo DONE $(date)
