#!/bin/bash
# s81-ctl-1011 coll engine gate (ADAPTER_CONTRACT_1011, engine 3): tb_s81ph_coll_sys +define+TB_CTRL = four
# dsfd_sp_collective_c slabs (dsfd_sp_collective + ot_s81_coll_job) driven by the real ot_s81_stage_seq (one coll job
# per message, credits QD 8) -- data exact vs the C8 reference engines AND done tags / order / timing / job_done.
# Mutants must FAIL: dropstart (a command never reaches the slab), wrongdesc (a descriptor names one record more),
# earlydone (endpoint MUT 5).  Run from the repo root:  run_coll_ctrl_gate.sh <out dir>   (exit 0 iff gate PASS)
set -u
O=$1; S=$(pwd); R=$S/rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh
mkdir -p $O
bash $R $O base -DTB_CTRL -GMAXCYC=200000 & p0=$!
bash $R $O mut_dropstart -DTB_CTRL -DTB_MUT_DROPSTART -GMAXCYC=60000 & p1=$!
bash $R $O mut_wrongdesc -DTB_CTRL -DTB_MUT_WRONGDESC -GMAXCYC=60000 & p2=$!
bash $R $O mut_earlydone -DTB_CTRL -GCMUT=5 -GMAXCYC=60000 & p3=$!
wait $p0; b=$?; wait $p1; m1=$?; wait $p2; m2=$?; wait $p3; m3=$?
v=PASS
[ $b -eq 0 ] || v=FAIL
for x in $m1 $m2 $m3; do [ $x -eq 1 ] || v=FAIL; done   # a mutant must build and FAIL (exit 1), not BUILD_FAIL (2)
echo "COLL_CTRL_GATE $v base=$b dropstart=$m1 wrongdesc=$m2 earlydone=$m3" | tee $O/verdict.log
[ $v = PASS ]
