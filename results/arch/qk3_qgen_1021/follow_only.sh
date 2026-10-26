#!/bin/bash
# QK3-QGEN: follow.sh (bind_gate DIAG_OPEN_OK -> census -> reset projection -> phase2 -> phase3) of a run dir whose GEN + strict bind are done
T=${1:?tag}; export DIAG_OPEN_OK=1 OT_SPLIT_FAULT_SOURCE_BITS=1
bash /srv/opentallas-scratch/claude/mu-die-qw/$T/follow.sh $T
