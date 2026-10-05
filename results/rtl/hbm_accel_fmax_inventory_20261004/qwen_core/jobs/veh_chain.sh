#!/bin/bash
# veh_chain.sh <a|b> <label> <snapshot> "<stages>" <successor flags...>: stages in sequence (one shared build)
b=$1; lab=$2; src=$3; sts=$4; shift 4
for st in $sts; do /srv/opentallas-scratch/claude/hbm-fmax-qcore/jobs/veh.sh $b $st $lab $src "$@"; done
