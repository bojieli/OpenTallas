#!/bin/bash
# CLK-TOOL-1 P0 replay: run ot_clk replay for one die config in a capped docker container (diagnostic probe).
# usage: replay.sh DIE MEM_G CPUS [--legacy] [--workers N]
set -u
D=$1; M=$2; C=$3; shift 3
W=/srv/opentallas-scratch2/claude/wt/clk-tool-1; O=/srv/opentallas-scratch2/claude/clk-tool-1/replay_$D
mkdir -p $O
docker run -d --name clktool1-$D --memory=${M}g --memory-swap=${M}g --cpus=$C --user $(id -u):$(id -g) \
  -v /srv/opentallas-scratch2:/srv/opentallas-scratch2 -w $W python:3.12 \
  bash -c "echo START \$(date) > $O/status; python -I tools/clk/ot_clk.py replay tools/clk/configs/$D.yaml --out $O $* > $O/replay.out 2>&1; echo EXIT \$? \$(date) >> $O/status"
