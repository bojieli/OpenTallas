#!/bin/bash
# emit new COORD-REVIEW-QUEUE lines that look like hand floorplan posts or address GEOM-VIS
S=$1; F=$S/v4/qlast.txt
[ -f $F ] || echo 48256 > $F
while true; do
  out=$(timeout 60 ssh -n -o ControlPath=none intel2 'cd ~/coord && git fetch -q origin coord/state; git show origin/coord/state:lanes/COORD-REVIEW-QUEUE.md' 2>/dev/null)
  if [ -n "$out" ]; then
    n=$(printf '%s\n' "$out" | wc -l); last=$(cat $F)
    if [ "$n" -gt "$last" ]; then
      printf '%s\n' "$out" | sed -n "$((last+1)),${n}p" | grep -E '^- ' | grep -iE 'floorplan|drawing|GEOM-VIS|WAIT-VISUAL|hand (top|placement|form)|vN2|QC-S28-C|ready12b|fix2|HFP-|HBM-HANDPLAN|lb_lep_m8|form B|re-pack|centre-only|center-only' | grep -v 'GEOM-VIS-[12345] ->' | cut -c1-260
      echo $n > $F
    fi
  fi
  sleep 300
done
