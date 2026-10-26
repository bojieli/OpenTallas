#!/bin/bash
# module-level RTL LEC gold vs new: mlec.sh <gold root> <new root> <out> <top> <chparam args...>
G=$1; N=$2; O=$3; T=$4; shift 4; P="$*"; B=/srv/opentallas-scratch2/claude/s81-bfcol-rtl/bench
FG=""; FN=""; for f in $(grep -v _bb.v $B/files.txt); do FG="$FG $G/$f"; FN="$FN $N/$f"; done
prep() { cat <<YS
read_verilog -defer -sv -DSYNTHESIS $B/icg_bb.v $1
${P:+chparam $P $T}
hierarchy -check -top $T
proc
$3
memory
flatten
opt_clean
async2sync
rename $T $2
design -stash $2
YS
}
{ prep "$FG" gold ""; prep "$FN" gate "check -assert"; cat <<YS
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
equiv_simple -seq 3
equiv_induct -seq 3
equiv_status -assert
YS
} > $O.ys
yosys -q -l $O.log $O.ys >/dev/null 2>&1; echo "rc=$?" > $O.rc
