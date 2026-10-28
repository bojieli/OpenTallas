#!/bin/bash
# DIE-QC-12 A0 step B: cluster leaf trees (TritonCTS per cluster net) + TT/FF arrivals.  run_cl.sh nk|nl
set -u; t=$1; A=/srv/opentallas-scratch2/claude/die-qc12-1028/a0trunk; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/$t; cd $A
python3 -I mkcltcl.py cl_$t.json cl_$t.tcl
docker run --rm --cpus=4 --memory=12g -v $P:/p:ro -v $A:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=TT ODB=/p/run/results/asap7/a0_${t}_1ck/base/3_place.odb CLTCL=/w/cl_$t.tcl OUT=/w/cl_$t.odb openroad -exit /w/cts_cl.tcl" > cts_cl_$t.log 2>&1; echo "cts rc $?"
for C in TT FF; do docker run --rm --cpus=2 --memory=8g -v $P:/p:ro -v $A:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=$C ODB=/w/cl_$t.odb OUT=/w/arr_cl_${t}_$C.txt openroad -exit /w/meas.tcl" > meas_cl_${t}_$C.log 2>&1 & done; wait; echo meas done
