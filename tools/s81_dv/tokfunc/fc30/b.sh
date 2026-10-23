#!/bin/bash
# STW-S81d-TOK: build + 2000-cycle idle of a cap30-framecal (die 3b4b975d) cut kit; DIE kit wrappers, frame flight, landing-reset none
R=/srv/opentallas-scratch/claude/stw-s81d-tok/fc30/cuts; c=$1
J=${J:-3} bash $R/K_$c/run_dv_slice.sh $R/K_$c $R/out_$c +NCYC=2000 +TRACE=$R/out_$c/trace.txt
