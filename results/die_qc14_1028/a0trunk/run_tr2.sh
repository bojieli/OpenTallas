#!/bin/bash
# DIE-QC-14: trunk_<tag>.json -> insert on cl_nkr.odb (a0k5 romleaf pin) -> TT/FF arrivals (placement RC) -> evtr2.  run_tr2.sh <tag>
set -u; g=$1; A=/srv/opentallas-scratch2/claude/die-qc14-1028/a0trunk; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/nk; cd $A
python3 -I mktrunktcl.py trunk_$g.json trunk_$g.tcl
docker run --rm --cpus=4 --memory=12g -v $P:/p:ro -v $A:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=TT ODB=/w/cl_nkr.odb TTCL=/w/trunk_$g.tcl OUT=/w/tr_$g.odb openroad -exit /w/ins_trunk.tcl" > ins_$g.log 2>&1; echo "ins rc $?"
for C in TT FF; do docker run --rm --cpus=2 --memory=8g -v $P:/p:ro -v $A:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=$C ODB=/w/tr_$g.odb OUT=/w/arr_tr_${g}_$C.txt openroad -exit /w/meas.tcl" > meas_tr_${g}_$C.log 2>&1 & done; wait
python3 -I evtr2.py $g
