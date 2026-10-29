#!/bin/bash
# DIE-KV-14 start-tree re-plan on the fishbone build: phase + planner options (retime-up, start skew = gate clk->Q range, skew-clean)
set -u; T=fb_inv_r150; TAG=$1; shift; R=/srv/opentallas-scratch2/claude/die-kv-14-1028; S=/srv/opentallas-scratch2/claude/wt/die-kv-14/tools/die_plan
PL=/srv/opentallas-scratch2/claude/die-kv-4-1027/pd9c/hm_r26q9c.json; P=${PROOF:-$R/proof_$T}; cd $R/ca_$T
STA="--sta-proof $P --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $P/droop_regions.json --sta-core-latency-ff 202.5 --sta-clock-cell inv"
python3 $S/count_align_bind.py ${T}_spice_xing_lpo.json --from-ocv --parts ocv $STA --start-tree clock --start-clean phase "$@" --samples 500 --out st_${TAG}_bind_parts.json > st_${TAG}_bind.log 2>&1; echo BIND_RC $?
mkdir -p $R/sta_$TAG; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar $R/sta_$TAG/ 2>/dev/null
python3 $S/die_sta_related.py $P --plan $PL --out $R/sta_$TAG --clock-cal spice --cppr-lca --count-align $R/ca_$T/st_${TAG}_bind_parts.json --count-align-key region --clock-ocv table --clock-droop shared --droop-regions $P/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv > $R/sta_$TAG.log 2>&1; echo STA_RC $?
head -3 $R/sta_$TAG.log
