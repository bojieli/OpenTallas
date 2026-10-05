#!/bin/bash
# W13b chain (2026-09-30 20:10): columns -> SM hardens (WC 0.833 ns, column SS models; ot-pve1/ot-pve2) -> die floorplans.
# args: <tc_col wrapper pid> <tc16 wrapper pid> <bd_col wrapper pid>.  Commits only on detached worktrees w13-smq12 / w13-smv13.
set -u
J=/tmp/claude-1000/w13jobs; WT=/tmp/claude-1000/wt; L=$J/logs; BASE=000ba089
EXS=155.103.253.78,155.103.253.133,155.103.253.191,155.103.253.16,155.103.253.39,155.103.253.114,ot-pve3
say(){ echo "[$(date -u +%H:%M:%S)] $*" >> $L/chain14.log; }
waitpid(){ while kill -0 $1 2>/dev/null; do sleep 60; done; }
clean(){ local ip; ip=$(grep -o 'worker [^ ]* (floor' $L/$1 | tail -1 | awk '{print $2}')
  case "$ip" in 155.*) timeout 120 ssh -i ~/.ssh/agidock_ot ubuntu@$ip "rm -rf $2";; ot-*) timeout 120 ssh $ip "rm -rf $2";; esac; say "cleaned $2 on ${ip:-?}"; }
take(){ (cd $1 && git ls-files -m -o --exclude-standard -- results) | while read -r f; do
  mkdir -p "$2/$(dirname "$f")"; cp -p "$1/$f" "$2/$f"; echo "$f"; done; }
prep(){ cd $WT/$1 && git checkout -q -f --detach $BASE && git clean -fdq -- results; }
commit(){ (cd $WT/$1 && xargs -a $3 git add -- && git commit -q -m "$2" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && say "$1 committed $(git rev-parse --short HEAD)"); }
ss(){ [ -f $1/results/physical_abi3/asap7/chip/abstracts/$2/${2}_ss.lib ]; }
say "chain14 start: tc_col $1, tc16 $2, bd_col $3"
(
  waitpid $1; say "tc_col ended"; clean h13_tc_col.log /home/ubuntu/w13wt/tc
  ss /home/ubuntu/w13wt/tc ot_gpu_tc_col || { say "tc_col has no SS model; sm_q not launched"; exit 1; }
  prep w13-smq12; take /home/ubuntu/w13wt/tc $WT/w13-smq12 > $J/q13.txt
  commit w13-smq12 "W13b: ot_gpu_tc_col (ot_v41_bmul2) at WC 0.833 ns (block, boundary, abstract, SS/FF corners and models)" $J/q13.txt
  say "launch sm_q"; bash $J/jobs/sm12.sh w13-smq12 ot_gpu_sm_q sm_q13 gpu_hbm_die_qwen $EXS 55 > $L/h13_sm_q.log 2>&1
  say "sm_q exit $?"; clean h13_sm_q.log $WT/w13-smq12
) &
(
  waitpid $2; say "tc16 ended"; clean h12_tc16.log $WT/w13-t16
  waitpid $3; say "bd_col ended"; clean h12_bd_col.log /home/ubuntu/w13wt/bd
  ss $WT/w13-t16 ot_gpu_tc16 && ss /home/ubuntu/w13wt/bd ot_gpu_bd_col || { say "tc16/bd_col SS model missing; sm_v not launched"; exit 1; }
  prep w13-smv13; { take $WT/w13-t16 $WT/w13-smv13; take /home/ubuntu/w13wt/bd $WT/w13-smv13; } > $J/v13.txt
  commit w13-smv13 "W13b: ot_gpu_tc16 and ot_gpu_bd_col (DEC_P0, P2M=10) at WC 0.833 ns (block, boundary, abstract, SS/FF corners and models)" $J/v13.txt
  say "launch sm_v"; bash $J/jobs/sm12.sh w13-smv13 ot_gpu_sm_v sm_v13 gpu_hbm_die_v41 $EXS 55 > $L/h13_sm_v.log 2>&1
  say "sm_v exit $?"; clean h13_sm_v.log $WT/w13-smv13
) &
wait
take $WT/w13-smq12 $WT/w13-smv13 > $J/fp13.txt
cd $WT/w13-smv13 && python3 tools/hbm_gpu_floorplan.py > $L/fp14.log 2>&1; say "floorplan exit $?"
say "chain14 done"
