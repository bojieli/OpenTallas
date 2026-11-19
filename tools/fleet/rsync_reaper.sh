#!/bin/bash
# COPY-REAPER-1119 (COORD, FABLE-FLOW-1150 A): receiver-side leftover `rsync --server` processes of THIS host: older than MIN_AGE (30 min) AND no IO progress over a 60 s window.
# Exact PIDs, cmdline re-checked before each kill, batches of 100 with a pause.  Touches nothing else (never openroad, docker, ot-job).  Run by ot-copy-reaper.timer from the hub; no LLM.
MIN_AGE=${MIN_AGE:-1800}; L=${L:-/tmp/flops_reap7.log}
echo "$(date -u +%T) start load $(cut -d' ' -f1 /proc/loadavg) rsync $(pgrep -xc rsync)" >> $L
snap() { for p in $(pgrep -x rsync); do
  a=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null); case "$a" in "rsync --server"*) ;; *) continue;; esac
  io=$(awk '/^(rchar|wchar)/{s+=$2} END{print s+0}' /proc/$p/io 2>/dev/null); et=$(ps -o etimes= -p $p 2>/dev/null | tr -d ' ')
  echo "$p ${io:-0} ${et:-0}"; done; }
snap > /tmp/flops_r1.txt; sleep 60; snap > /tmp/flops_r2.txt
join <(sort /tmp/flops_r1.txt) <(sort /tmp/flops_r2.txt) | awk -v m=$MIN_AGE '$2==$4 && $5>=m {print $1}' > /tmp/flops_victims.txt
n=$(wc -l < /tmp/flops_victims.txt); echo "$(date -u +%T) candidates $n (of $(wc -l < /tmp/flops_r2.txt) rsync --server)" >> $L
k=0; b=0
while read p; do
  a=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null); case "$a" in "rsync --server"*) ;; *) continue;; esac
  kill -TERM $p 2>/dev/null && k=$((k+1)); b=$((b+1))
  [ $b -ge 100 ] && { b=0; sleep 20; echo "$(date -u +%T) batch done, killed $k, load $(cut -d' ' -f1 /proc/loadavg)" >> $L; }
done < /tmp/flops_victims.txt
sleep 30
echo "$(date -u +%T) end killed $k, load $(cut -d' ' -f1-3 /proc/loadavg) rsync $(pgrep -xc rsync) sshd-session $(pgrep -xc sshd-session)" >> $L
