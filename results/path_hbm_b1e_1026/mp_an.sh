#!/bin/bash
D=/srv/opentallas-scratch2/claude/path-hbm/b1d_1026/plan_b1d; O=/srv/opentallas-scratch2/claude/path-hbm/b1e_1026/mp_an_b1d
mkdir -p $O; cd $D
python3 /srv/opentallas-scratch2/claude/path-hbm/b1e_1026/mp_analysis_tools/die_infra.py master-plan die_plan.json --out $O --entries entries.json --no-render > $O.log 2>&1; echo $? > $O.exit
