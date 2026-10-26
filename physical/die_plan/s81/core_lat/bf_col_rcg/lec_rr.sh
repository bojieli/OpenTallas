#!/bin/bash
# RTL-vs-RTL LEC of ot_v41_bf_col: old (gold) vs new (gate), kit parameters (params.txt), inside the ORFS image.
# usage: lec_rr.sh <gold src root> <gate src root> <out dir>
G=$1; N=$2; O=$3; B=$(cd $(dirname $0); pwd); mkdir -p $O
P=""; for kv in $(cat $B/params.txt); do P="$P -set ${kv%%=*} ${kv#*=}"; done
FG=""; FN=""; for f in $(cat $B/files.txt); do FG="$FG $G/$f"; FN="$FN $N/$f"; done
prep() { cat <<YS
read_verilog -sv -DSYNTHESIS $B/icg_bb.v $1
chparam $P ot_v41_bf_col
hierarchy -check -top ot_v41_bf_col
proc
memory
setattr -mod -unset keep_hierarchy *
flatten
opt_clean
opt_merge -share_all
opt_clean
opt_merge -share_all
opt_clean
stat
rename ot_v41_bf_col $2
design -stash $2
YS
}
{ prep "$FG" gold; prep "$FN" gate; cat <<YS
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
select -count gold/t:ICGx1_ASAP7_75t_R
select -count gate/t:ICGx1_ASAP7_75t_R
async2sync gold gate
equiv_make gold gate equiv
hierarchy -top equiv
equiv_struct
equiv_simple -seq 3
equiv_induct
equiv_status
equiv_status -assert
YS
} > $O/lec_rr.ys
yosys -l $O/lec_rr.log -q $O/lec_rr.ys; rc=$?; echo "rc=$rc" > $O/exit; echo rc=$rc
