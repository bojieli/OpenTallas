#!/bin/bash
T=$1; R=/srv/opentallas-scratch/claude/codex-qdie-2000
/home/ubuntu/bin/ot-run --mem 16 --threads 4 --disk 1 --priority die --dir $R/$T -- bash $R/$T/pre.sh
echo "pre rc=$?"
