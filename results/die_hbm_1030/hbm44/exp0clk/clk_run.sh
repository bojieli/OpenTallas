#!/bin/bash
cd /srv/opentallas-scratch2/claude/wt/die-hbm-42; ulimit -v 40000000
for P in d44c d44f; do ( nice -n 5 python3 tools/die_plan/die_clock.py run /srv/opentallas-scratch2/claude/die-hbm-44/plan/$P/die_plan.json --out /srv/opentallas-scratch2/claude/die-hbm-44/clk/$P --core-early pad --corner TT --corner FF > /srv/opentallas-scratch2/claude/die-hbm-44/clk/$P.log 2>&1; echo $? > /srv/opentallas-scratch2/claude/die-hbm-44/clk/$P.rc ) & done; wait
