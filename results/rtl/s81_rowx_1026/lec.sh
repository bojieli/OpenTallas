#!/bin/bash
# S81-ROWX: RTL-vs-RTL LEC of dsdv_svc_att: gold = pre-ROWX (main), gate = ROWX source with ROWX = 0 (default),
# OT_SVC_ALLQ (877 die define), engine blackboxed (unchanged), PFIFO 8 in both (array depth only).
# usage: lec.sh <gold.sv> <gate.sv> <eng_bb.v> <outdir> [ROWX value for gate, default 0]
G=$1; N=$2; BB=$3; O=$4; RXV=${5:-0}; mkdir -p $O
python3 $(dirname $0)/desv.py $G $O/gold.sv; python3 $(dirname $0)/desv.py $N $O/gate.sv; G=$O/gold.sv; N=$O/gate.sv
prep() { cat <<YS
read_verilog -sv -DOT_SVC_ALLQ -DSYNTHESIS $BB $1
chparam -set PFIFO 8 $3 dsdv_svc_att
hierarchy -check -top dsdv_svc_att
proc
memory
flatten
opt_clean
opt -fast
stat
rename dsdv_svc_att $2
design -stash $2
YS
}
{ prep "$G" gold ""; prep "$N" gate "-set ROWX $RXV"; cat <<YS
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
async2sync
equiv_make -blacklist /dev/null gold gate equiv
hierarchy -top equiv
equiv_struct
equiv_simple
equiv_induct
equiv_status
equiv_status -assert
YS
} > $O/lec.ys
timeout 2700 yosys -l $O/lec.log -q $O/lec.ys; rc=$?; echo "rc=$rc" > $O/exit; echo rc=$rc
