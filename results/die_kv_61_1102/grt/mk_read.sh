#!/bin/bash
# DIE-KV-61/grt (= DIE-KV-58 mk_read.sh): both-edge SDF readout tcl for ctree CTREE, run dir /n/out_CORNER (mounted grt_<V>), template = DIE-KV-58 read_st.tcl
# usage: mk_read.sh CTREE.v OUT.tcl
CT=$1; OUT=$2; B=/home/ubuntu/scratch-root/claude/die-kv-61/grt
ODD=$(python3 $B/oddgen.py $CT) || exit 1
python3 - $B/in/die-kv-58/clk/read_st.tcl "$ODD" $OUT <<"PY"
import sys
src,odd,out=sys.argv[1:4]
o=[]
for l in open(src).read().splitlines():
    if l.startswith("set ot_odd [dict create "): l="set ot_odd [dict create "+odd+"]"
    if l.startswith("set O /n/out_st_"): l="set O /n/out_$::env(CORNER)"
    if l.startswith("# DIE-KV-58/clk"): l="# DIE-KV-61/grt: DIE-KV-58 read_st.tcl, ot_odd regenerated from the new ctree (oddgen.py), run dir /n/out_CORNER"
    o.append(l)
open(out,"w").write("\n".join(o)+"\n")
PY
