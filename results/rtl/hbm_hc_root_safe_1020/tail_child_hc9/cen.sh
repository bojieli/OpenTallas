#!/bin/bash
# census.sh NAME : native32 census of mapped_NAME.v (top) and retained_NAME.v (top_bfc)
set -u; d=$(pwd); n=$1; top=ot_hbm_hc_tail_child_static
rm -rf $d/c_$n; mkdir -p $d/c_$n && cd $d/c_$n && tar xzf $d/src.tgz
libs=""; for f in $d/libs/*.lib; do libs="$libs --liberty $f"; done
python3 tools/ref_tile/native_census.py --netlist $d/mapped_$n.v --top $top --out $d/census_p_$n.json $libs > $d/census_p_$n.log 2>&1; python3 $d/summ.py $d/census_p_$n.json > $d/summ_p_$n.txt 2>&1
python3 tools/ref_tile/native_census.py --netlist $d/retained_$n.v --top ${top}_bfc --out $d/census_r_$n.json $libs > $d/census_r_$n.log 2>&1; python3 $d/summ.py $d/census_r_$n.json > $d/summ_r_$n.txt 2>&1
cd $d && rm -rf $d/c_$n
