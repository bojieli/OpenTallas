#!/bin/bash
# usage: refcheck.sh names.txt  -> for each basename, count mentions in queue (last 40000 lines), all lane reports today, handoffs, and live ps on all hosts
S=/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad
Q=~/coord/lanes/COORD-REVIEW-QUEUE.md
for h in intel1 intel2 epyc2 epyc4 epyc5 epyc6; do timeout 40 ssh -n -o ControlPath=none $h 'ps -eo args' > $S/ps.$h 2>/dev/null; done
ps -eo args > $S/ps.localhost
tail -n 12000 $Q > $S/q_recent.txt
ls ~/coord/lanes/*.md ~/coord/handoff/*.json 2>/dev/null | xargs -d '\n' grep -l . 2>/dev/null > /dev/null
while read n; do
  q=$(grep -c -F -- "/$n" $S/q_recent.txt)
  qb=$(grep -c -w -F -- "$n" $S/q_recent.txt)
  l=$(grep -l -F -- "$n" ~/coord/lanes/CODEX-*-1113.md ~/coord/lanes/_RESTART_1108b.md 2>/dev/null | wc -l)
  p=$(cat $S/ps.* | grep -c -F -- "$n")
  echo -e "$n\tqueue_path=$q\tqueue_word=$qb\tcodex_reports=$l\tlive_ps=$p"
done < "$1"
