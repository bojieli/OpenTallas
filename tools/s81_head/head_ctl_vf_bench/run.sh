#!/bin/bash
# DIE-HEAD-83 hd_ctl vF lockstep benches + mutants. Usage: run.sh OLD_RTL NEW_RTL OUT
set -u; OLD=$1; NEW=$2; O=$3; B=$(cd $(dirname $0) && pwd)
python3 -I $B/mk.py $OLD $NEW $O || exit 2
cp $B/sram.v $O/; cd $O
sed 's/if (st == S_PRE) x_deq <=/if (st == S_RD) x_deq <=/' new.v > mut_seq.v
sed 's/else op_q1 <= ri_v \&\& ri_q\[3:1\] == K_XB \&\& rt_q\[31\] \&\&/else op_q1 <= ri_v \&\& ri_q[3:1] == K_XB \&\& rt_q[31] || 1b0 \&\&/' new.v | sed "s/rt_q\[31\] || 1b0 \&\&/rt_q[31]; \/\/ MUT ownership dropped\n                  wire mut_unused = /" > mut_op.v
sed 's/next_date<=first?nd_off:nd_run;/next_date<=first?nd_run:nd_off;/' new.v > mut_iss.v
for f in mut_seq.v mut_op.v mut_iss.v; do cmp -s new.v $f && { echo "MUTANT $f not applied"; exit 3; }; done
comp() { iverilog -g2012 -DNEWMOD=$3 -s $2 -o $1 old.v $4 sram.v $B/$2.sv 2>&1 | grep -v -i warning | head -5; }
comp seq.vvp tb_seq ot_dsrom_mtp_seq_fan new.v; comp seqm.vvp tb_seq ot_dsrom_mtp_seq_fan mut_seq.v
comp iss.vvp tb_iss ot_s81hd_static_issue new.v; comp issm.vvp tb_iss ot_s81hd_static_issue mut_iss.v
comp hsf.vvp tb_hsf ot_s81hd_ctl_hsf0_static new.v; comp hsfm.vvp tb_hsf ot_s81hd_ctl_hsf0_static mut_op.v
for s in 1 2 3 4; do vvp -n seq.vvp +seed=$s +n=80000 | grep -E 'SEQ|MISMATCH' | tail -2; done
vvp -n seqm.vvp +seed=1 +n=80000 | grep -E 'SEQ' | sed 's/^/MUTANT /'
for s in 1 2 3; do vvp -n iss.vvp +seed=$s +n=300000 | grep -E 'ISS' | tail -2; done
vvp -n issm.vvp +seed=1 +n=300000 | grep -E 'ISS' | sed 's/^/MUTANT /'
for s in 1 2; do vvp -n hsf.vvp +seed=$s +n=8000 | grep -E 'HSF|MISMATCH' | tail -2; done
vvp -n hsfm.vvp +seed=1 +n=8000 | grep -E 'HSF' | sed 's/^/MUTANT /'
echo BENCH_DONE
