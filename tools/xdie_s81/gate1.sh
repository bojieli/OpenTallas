#!/bin/bash
# gate1.sh <tag> <name> <LAT> <PER> [verilator args]: one configuration with the compiled deadlines on the dense
# calendar (GAP cycles between instances, default 100), no mutants (cwd = staged repo root)
set -u; T=$1; N=$2; LT=$3; PR=$4; shift 4; O=out_$T; mkdir -p $O
[ -f $O/g/NS ] || python3 tools/xdie_s81/gen_golden.py --out $O/g --gap ${GAP:-100} --lat S=$LT,N=$LT --per S=$PR,N=$PR > $O/gen.txt 2>&1
J=6 bash tools/xdie_s81/run_xdie_s81.sh $O $N $O/g ep "$@" > $O/$N.txt 2>&1; echo "EXIT $?" >> $O/$N.txt
grep -E "^XDIE_LINK" $O/$N/run.log >> $O/$N.txt; cat $O/$N.txt
