#!/bin/bash
D=/srv/opentallas-scratch2/claude/path-hbm-r7-1026; cd /srv/opentallas-scratch2/claude/wt/path-hbm-r7-1026
B=/srv/opentallas-scratch2/claude/master-plan-r6-1026/plan_b1e2
run(){ n=$1; shift; rm -rf $D/$n; prlimit --as=40000000000 /usr/bin/time -v python3 -u tools/die_plan/die_infra.py master-plan "$@" --out $D/$n > $D/$n.log 2>&1; }
run b1e2_c4x4 $B/die_plan.json --entries $B/entries.json --tree-lattice c4x4 --tree-commensurate regional &
run b1e2_c8x4 $B/die_plan.json --entries $B/entries.json --tree-lattice c8x4 --tree-commensurate regional &
run b1e2_c2x2 $B/die_plan.json --entries $B/entries.json --tree-lattice c2x2 --tree-commensurate regional &
wait
