#!/bin/bash
# usage: bind.sh PLAN OUT ASBUILT : elab then strict bind
cd /home/ubuntu/scratch-root/claude/die-qc-63-red/wt; P=$1; O=$2; M=$3; mkdir -p $O
python3 -I tools/die_plan/bind.py elab $P --out $O --asbuilt $M --mem 28 > $O/elab.log 2>&1; echo ELAB_RC $? >> $O/elab.log
python3 -I tools/die_plan/bind.py bind $P --out $O --strict --asbuilt $M > $O/bind.log 2>&1; echo BIND_RC $? >> $O/bind.log
