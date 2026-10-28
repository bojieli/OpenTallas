#!/bin/bash
# DIE-QC-18 nk: a0cl47 split (split.py) -> cluster CTS on base 3_place -> TT/FF arrivals -> clins -> a0k5 pin db (QC-14 recipe)
set -u; N=/srv/opentallas-scratch2/claude/die-qc18-1028/nk; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/nk; cd $N
python3 -I mkcltcl.py cl_nk.json cl_nk.tcl
docker run --rm --name qc18-nk-cts --cpus=4 --memory=12g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=TT ODB=/p/run/results/asap7/a0_nk_1ck/base/3_place.odb CLTCL=/w/cl_nk.tcl OUT=/w/cl_nk.odb openroad -exit /w/cts_cl.tcl" > cts_cl_nk.log 2>&1; echo "cts rc $?"
for C in TT FF; do docker run --rm --name qc18-nk-meas-$C --cpus=2 --memory=8g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=$C ODB=/w/cl_nk.odb OUT=/w/arr_cl_nk_$C.txt openroad -exit /w/meas.tcl" > meas_cl_nk_$C.log 2>&1 & done; wait
python3 -I clins.py > clins.log
docker run --rm --name qc18-nk-relef --cpus=2 --memory=8g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/wdef.tcl && openroad -exit /w/relef.tcl" > relef.log 2>&1; echo "relef rc $?"
echo "prep done $(date)"
