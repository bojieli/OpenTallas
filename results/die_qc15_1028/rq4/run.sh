#!/bin/bash
A=/srv/opentallas-scratch2/claude/die-qc15-1028/rq4; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/nk; cd $A
for C in TT FF; do docker run --rm --name qc15-rq4-$C --cpus=4 --memory=16g -v $P:/p:ro -v $A:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=$C ODB=/w/tr_q4.odb OUT=/w/arr_rq4_$C.txt openroad -threads 4 -exit /w/grt.tcl; echo EXIT \$?" > grt_$C.log 2>&1 & done; wait; echo done $(date)
