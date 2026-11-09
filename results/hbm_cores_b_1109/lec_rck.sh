#!/bin/bash
# ROOT-MERGE-54: default-configuration equivalence, main vs RCK tip, for the blocks with unconditional keep/dont_touch
L=/srv/opentallas-scratch3/claude/rm54/lec_rck; R=/srv/opentallas-scratch3/claude/rm48/repo
MAIN=ed5be48cd49; TIP=9c2a8b7c9f8a
rm -rf $L; mkdir -p $L/main $L/tip $L/w; cd $R
git archive $MAIN rtl/dsrom_sys/s81_link rtl/common | tar -x -C $L/main
git archive $TIP  rtl/dsrom_sys/s81_link rtl/common | tar -x -C $L/tip
side(){ s=$1; top=$2; D=/d/$s/rtl/dsrom_sys/s81_link
cat <<Y
design -reset
read_slang --top $top -I $D -I /d/$s/rtl/common $D/ot_s81_kp4_common.sv $D/ot_s81_kp4_bm.sv $D/$top.sv
prep -flatten -top $top
memory_map
opt_clean -purge
tee -o /d/w/$top.$s.prep.stat stat
design -save ${s}_prep
synth -flatten -top $top -noabc
tee -o /d/w/$top.$s.syn.stat stat
design -load ${s}_prep
rename $top ${3}
design -stash ${3}_st
Y
}
for top in ot_s81_kp4_enc ot_s81_kp4_dsyn; do
{ side main $top gold; side tip $top gate
cat <<Y
design -reset
design -copy-from gold_st -as gold gold
design -copy-from gate_st -as gate gate
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -undef
equiv_induct -undef
tee -o /d/w/$top.equiv.txt equiv_status
equiv_status -assert
Y
} > $L/w/$top.ys
( timeout 1500 docker run --rm --name rm54_lec_$top --memory=32g --cpus=8 -v $L:/d openroad/orfs:asap7lock yosys -q -l /d/w/$top.log /d/w/$top.ys; echo "$top rc $?" >> $L/rc.txt ) &
done
wait; echo ALLDONE >> $L/rc.txt
