#!/bin/bash
# emits one line per NEW terminal/state fact; safe to re-arm (seen file persists)
cd /
SP=/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad
SEEN=$SP/watch.seen; touch $SEEN
S="ssh -n -o ControlPath=none -o ConnectTimeout=20"
START=$(date '+%Y-%m-%d %H:%M')
while true; do
  {
    $S intel2 'cd /
      grep -E "slice_station__t(24__cleece78ec|29__clc7772371)" ~/coord/autopilot/auto_resign.tsv | grep eu-s81 | cut -f1,4,7,10 | sed "s/^/RESIGN /"
      grep -E "CLASSIFY .*ot_s81sl_leaf__t(15|36|40__clf8bbdae1|47|59|65|21|46) " ~/coord/autopilot/log.txt | awk -v s="2026-11-08 23:30" "\$0>=s" | cut -c1-260 | sed "s/^/LEAF /"
      for l in t16w2 rxb_vF; do tail -1 ~/s81-types-13-logs/$l.otrun.log | grep -E "ot-run: (RAN|NOT)" | cut -c1-120 | sed "s/^/JOB $l /"; done
      docker ps --format "{{.Names}}" | grep -q prd-t24c648 || { echo "ECO t24c648 container gone"; ls /srv/opentallas-scratch2/claude/s81-types-12/eco/t24c648/ | tr "\n" " " | sed "s/^/ECO t24c648 dir: /"; echo; }
    ' 2>/dev/null
    $S epyc2 'cd /
      docker ps --format "{{.Names}}" | grep -q rxs_vG_region || echo "RXS vG container gone"
      for k in h9r0p2 h9r1; do f=$(ls /srv/opentallas-scratch3/claude/s81-colh-10/kits/$k/gen/*/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null); [ -n "$f" ] && echo "COLH $k GRT finished"; done
      for r in t16w rxb_vF_dmem_north; do d=/srv/opentallas-scratch2/claude/s81-types-13/$r; ls $d/FAIL_* 2>/dev/null | sed "s/^/FAILMARK /"; for st in place cts grt; do [ -f $d/run/layout_review/$st/.stamp ] && echo "RENDER $r $st"; done; done
    ' 2>/dev/null
    $S epyc5 'cd /; f=$(ls /srv/opentallas-scratch3/claude/s81-colh-10/kits/h10r0p4/gen/*/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null); [ -n "$f" ] && echo "COLH h10r0p4 GRT finished"' 2>/dev/null
    $S epyc6 'cd /; docker ps --format "{{.Names}}" | grep -q tx_vG_pq4 || echo "TX vG container gone"' 2>/dev/null
    $S epyc4 'cd /; ls -d /srv/opentallas-scratch2/claude/s81-types-12/eco/t6/i1* 2>/dev/null | head -1 | sed "s/^/T6 started epyc4: /"; docker ps --format "{{.Names}}" | grep -q prd-t6-i1t || { ls -d /srv/opentallas-scratch2/claude/s81-types-12/eco/t6/i1t >/dev/null 2>&1 && echo "ECO t6 container gone"; }' 2>/dev/null
    $S intel2 'cd /; for l in eco_t38 eco_t47; do tail -1 ~/s81-types-13-logs/$l.otrun.log | grep -E "ot-run: (RAN|NOT)" | cut -c1-120 | sed "s/^/JOB $l /"; done; grep -q "waiting for load" ~/s81-types-13-logs/eco_t47.otrun.log && grep -q "admitted on" ~/s81-types-13-logs/eco_t47.otrun.log && echo "ECO t47 admitted"' 2>/dev/null
  } | sort -u > $SP/watch.now
  comm -13 <(sort -u $SEEN) $SP/watch.now | while IFS= read -r l; do echo "$l"; echo "$l" >> $SEEN; done
  sleep 180
done
