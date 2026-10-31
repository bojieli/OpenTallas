#!/bin/bash
# DIE-HBM-44: d44c freeze G2 at 50 it: die probe (clock+reset spine M8/M9) + worst-8 partition FT probes
cd /srv/opentallas-scratch2/claude/wt/die-hbm-42; ulimit -v 60000000
python3 tools/die_plan/g2.py die /srv/opentallas-scratch2/claude/die-hbm-44/plan/d44c/die_plan.json --out /srv/opentallas-scratch2/claude/die-hbm-44/g50/die > /srv/opentallas-scratch2/claude/die-hbm-44/g50/gen_die.log 2>&1; echo die $? >> /srv/opentallas-scratch2/claude/die-hbm-44/g50/gen.rc
python3 tools/die_plan/g2.py part /srv/opentallas-scratch2/claude/die-hbm-44/plan/d44c/die_plan.json --out /srv/opentallas-scratch2/claude/die-hbm-44/g50/part --worst 8 > /srv/opentallas-scratch2/claude/die-hbm-44/g50/gen_part.log 2>&1; echo part $? >> /srv/opentallas-scratch2/claude/die-hbm-44/g50/gen.rc
