#!/bin/bash
# HBM-COMPOSE route_supply (advisory) on a plan dir, main tree of the hbm-cut-1111 worktree. usage: rs.sh PLANDIR OUTDIR
set -u
R=/srv/opentallas-scratch2/claude/wt/hbm-cut-1111; P=$1; O=$2; mkdir -p $O
cd $R
nice -n 10 python3 -I tools/die_plan/route_supply.py $P/die_plan.json --die hbm --repo . --ref-dirs $P --out $O > $O/rs.stdout 2> $O/rs.stderr
echo "rc $?" >> $O/rs.stdout
