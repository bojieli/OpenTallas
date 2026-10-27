#!/bin/bash
D=/srv/opentallas-scratch2/claude/path-hbm-r8-1026; cd /srv/opentallas-scratch2/claude/wt/path-hbm-r8-1026
B=/srv/opentallas-scratch2/claude/master-plan-r6-1026/plan_b1e2
run(){ n=$1; shift; rm -rf $D/$n; prlimit --as=40000000000 /usr/bin/time -v python3 -u tools/die_plan/die_infra.py master-plan "$@" --out $D/$n > $D/$n.log 2>&1; }
run id_b1e2_reg $B/die_plan.json --entries $B/entries.json --tree-commensurate regional &
run tr_b1e2_reg $B/die_plan.json --entries $B/entries.json --tree-commensurate regional --tree-roads &
run tr_banks_reg $D/t_banks/die_plan.json --entries $D/t_banks/entries.json --tree-commensurate regional --tree-roads &
wait
