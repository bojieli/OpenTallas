#!/bin/bash
# exit when new queue lines mention drawings/visual items (or after max min); prints them
S=$1; MAX=${2:-40}; F=$S/v4/qlast.txt; t0=$(date +%s)
while true; do
  out=$(timeout 60 ssh -n -o ControlPath=none intel2 'cd ~/coord && git fetch -q origin coord/state; git show origin/coord/state:lanes/COORD-REVIEW-QUEUE.md' 2>/dev/null)
  if [ -n "$out" ]; then
    n=$(printf '%s\n' "$out" | wc -l); last=$(cat $F)
    if [ "$n" -gt "$last" ]; then
      hit=$(printf '%s\n' "$out" | sed -n "$((last+1)),${n}p" | grep -E '^- ' | grep -iE 'drawing|GEOM-VIS-6|WAIT-VISUAL|WAIT-FORM|hand floorplan|QC-S28-C|ready12b|HFP-|HBM-HANDPLAN|lb_lep_m8|re-pack|svc_hi|svc_lo|ring pilot|REVIEW-REQUEST|REVIEW REQUEST|q2n2|form C2|layout_review' | grep -v 'GEOM-VIS-[123456] ->' | cut -c1-400)
      echo $n > $F
      if [ -n "$hit" ]; then echo "$hit"; exit 0; fi
    fi
  fi
  [ $(( $(date +%s) - t0 )) -gt $((MAX*60)) ] && { echo TIMEOUT; exit 0; }
  sleep 240
done
