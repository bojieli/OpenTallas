#!/bin/bash
# DIE-HEAD-19 what-if: gate only (die_sta_related --count-align ... --ca-ring SPEC) on the DH18 r1 proof/bind (unchanged)
set -u
N=$1; G=/srv/opentallas-scratch2/claude/die-head-18/clk18_r1; P=$G/proof; O=/srv/opentallas-scratch2/claude/die-head-19/whatif/$N
MT=/srv/opentallas-scratch2/claude/wt/die-head-18/tools/die_plan; rm -rf $O; mkdir -p $O; cd $MT
python3 die_sta_related.py $P --plan $G/die_plan_root_sp5_lat545.3.json --out $O/sta --corner TT --corner FF --core-latency-ff 445.7 \
  --droop-regions $P/droop_regions.json --count-align $G/ca/bind_idreg.json --count-align-key region --clock-cal spice \
  --cppr-lca --clock-ocv table --clock-droop shared --clock-cell inv2 --ca-ring /srv/opentallas-scratch2/claude/die-head-19/whatif/ring_$N.json > $O/sta.log 2>&1; echo "$N RC $?"
grep -E "COUNT-ALIGN (TT|FF)" $O/sta.log | cut -c1-260
