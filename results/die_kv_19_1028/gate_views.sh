#!/bin/bash
# DIE-KV-19 KV freeze gate in VIEW mode: the DIE-KV-15 gate of record (proofF_fb, st_fall count-align parts, main die_sta_related,
# table OCV, spice, cppr-lca, shared droop, inv, HB4, FF 202.5) + every signed KV core view (--core-view, match-pins ON).
# MODE=view (fail closed where no view) and MODE=declared (planning: plan insertion where no view; verdict DECLARED).
set -u
R=/srv/opentallas-scratch2/claude/die-kv-15-1028; S=/srv/opentallas-scratch2/claude/wt/die-kv-16/tools/die_plan
O=/srv/opentallas-scratch2/claude/die-kv-19-1028; V=$O/views; P=$R/proofF_fb; PL=$R/hm_r26q15c.json
CV=""; for d in $V/*/view/*; do CV="$CV --core-view $(basename $d)=$d"; done
for M in ${MODES:-declared view}; do
  mkdir -p $O/sta_views_$M; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar $O/sta_views_$M/ 2>/dev/null
  python3 $S/die_sta_related.py $P --plan $PL --out $O/sta_views_$M --clock-cal spice --cppr-lca \
    --count-align $R/ca_fb_inv_r150/st_fall_bind_parts.json --count-align-key region --clock-ocv table --clock-droop shared \
    --droop-regions $P/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv $CV --core-insertion $M \
    > $O/sta_views_$M.log 2>&1; echo STA_VIEWS_${M}_RC $?
  head -5 $O/sta_views_$M.log
done
