#!/bin/bash
# Pin a source snapshot of the worktree on ot-epyc1tb: sync.sh <snapshot name>
set -e
WT=/home/ubuntu/hbm-fmax-qcore-20261004
R=/srv/opentallas-scratch/claude/hbm-fmax-qcore
ssh ot-epyc1tb "mkdir -p $R/$1"
rsync -a --delete --exclude '__pycache__' $WT/rtl $WT/tools $WT/physical $WT/configs ot-epyc1tb:$R/$1/
echo synced $1
