#!/bin/bash
# DIE-KV-11: START-TREE-1 (91c2e9fec3, git archive st1/, no fork) --start-tree clock on the built re-tree local form (kit_rt
# proof), K with OCV (clock_variation=table, spice, cppr-lca, shared droop), phase and width clean; then die STA gate re-check.
set -u
R=/srv/opentallas-scratch2/claude/die-kv-11-1028; S=$R/st1/tools/die_plan; PL=/srv/opentallas-scratch2/claude/die-kv-4-1027/pd9c/hm_r26q9c.json
cd $R/cart
STA="--sta-proof $R/proofrt --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $R/proofrt/droop_regions.json --sta-core-latency-ff 202.5"
for M in width phase; do
  python3 $S/count_align_bind.py rt_spice_xing_lpo.json --from-ocv --parts ocv $STA --start-tree clock --start-clean $M --samples 500 --out st_${M}_bind_parts.json > st_${M}_bind.log 2>&1; echo BIND_${M}_RC $? $(date -Is)
done
for M in width phase; do
  mkdir -p $R/sta_st_$M; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar $R/sta_st_$M/ 2>/dev/null
  python3 $S/die_sta_related.py $R/proofrt --plan $PL --out $R/sta_st_$M --clock-cal spice --cppr-lca --count-align $R/cart/st_${M}_bind_parts.json --count-align-key region --clock-ocv table --clock-droop shared --droop-regions $R/proofrt/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 > $R/sta_st_$M.log 2>&1; echo STA_${M}_RC $? $(date -Is)
done
echo ST_DONE
