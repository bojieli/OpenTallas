#!/bin/bash
# s81-ctl-1011 coll engine gate (ADAPTER_CONTRACT_1011, engine 3): tb_s81ph_coll_sys +define+TB_CTRL = four
# dsfd_sp_collective_c slabs (dsfd_sp_collective + ot_s81_coll_job) driven by the real ot_s81_stage_seq (one coll job
# per message, credits QD 8) -- data exact vs the C8 reference engines AND done tags / order / timing / job_done.
# Mutants must FAIL: dropstart (a command never reaches the slab), wrongdesc (a descriptor names one record more),
# earlydone (endpoint MUT 5).  Run from the repo root:  run_coll_ctrl_gate.sh <out dir>   (exit 0 iff gate PASS)
set -u
O=$1; S=$(pwd); R=$S/rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh
mkdir -p $O
bash $R $O base -DTB_CTRL +define+OT_S81PH_COLL_JOB -GMAXCYC=200000 & p0=$!
bash $R $O mut_dropstart -DTB_CTRL +define+OT_S81PH_COLL_JOB -DTB_MUT_DROPSTART -GMAXCYC=60000 & p1=$!
bash $R $O mut_wrongdesc -DTB_CTRL +define+OT_S81PH_COLL_JOB -DTB_MUT_WRONGDESC -GMAXCYC=60000 & p2=$!
bash $R $O mut_earlydone -DTB_CTRL +define+OT_S81PH_COLL_JOB +define+OT_S81PH_COLL_JOB_MUT=5 -GMAXCYC=60000 & p3=$!
bash $R $O noctrl -GMAXCYC=200000 & p4=$!      # the same plan without control: the cycle price of the binding
wait $p0; b=$?; wait $p1; m1=$?; wait $p2; m2=$?; wait $p3; m3=$?; wait $p4; n0=$?   # wave 1 (<= 5 builds of ~15 GB)
# the production slab composition (split3cr tiles: the endpoint tile dsfd_coll_job sits under dsfd_coll_cb)
SPL="+define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 +define+OT_S81PH_COLL_OQPIPE +define+OT_S81PH_COLL_QPIPE +define+OT_S81PH_COLL_SPLIT +define+OT_S81PH_COLL_CR +define+OT_S81PH_LANE_CR +define+OT_S81PH_COLL_PULL +define+OT_S81PH_COLL_TREP"
bash $R $O base_split -DTB_CTRL +define+OT_S81PH_COLL_JOB $SPL -GMAXCYC=200000 & p5=$!
bash $R $O noctrl_split $SPL -GMAXCYC=200000 & p6=$!
bash $R $O mut_dropstart_split -DTB_CTRL +define+OT_S81PH_COLL_JOB $SPL -DTB_MUT_DROPSTART -GMAXCYC=60000 & p7=$!
bash $R $O mut_earlydone_split -DTB_CTRL +define+OT_S81PH_COLL_JOB $SPL +define+OT_S81PH_COLL_JOB_MUT=5 -GMAXCYC=60000 & p8=$!
wait $p5; bs=$?; wait $p6; ns=$?; wait $p7; m4=$?; wait $p8; m5=$?
v=PASS
[ $b -eq 0 ] || v=FAIL
for x in $m1 $m2 $m3 $m4 $m5; do [ $x -eq 1 ] || v=FAIL; done   # a mutant must build and FAIL (exit 1), not BUILD_FAIL (2)
[ $n0 -eq 0 ] || v=FAIL
[ $bs -eq 0 ] || v=FAIL
[ $ns -eq 0 ] || v=FAIL
cb=$(grep -oE "dut_last [0-9]+" $O/base.log | awk '{print $2}'); cn=$(grep -oE "dut_last [0-9]+" $O/noctrl.log | awk '{print $2}')
fs=$(grep -oE "first_send [0-9]+" $O/base.log | awk '{print $2}')
cbs=$(grep -oE "dut_last [0-9]+" $O/base_split.log | awk '{print $2}'); cns=$(grep -oE "dut_last [0-9]+" $O/noctrl_split.log | awk '{print $2}')
echo "COLL_CTRL_GATE $v base=$b dropstart=$m1 wrongdesc=$m2 earlydone=$m3 noctrl=$n0 base_split=$bs noctrl_split=$ns dropstart_split=$m4 earlydone_split=$m5 cycles ctrl $cb vs noctrl $cn, split3cr ctrl $cbs vs noctrl $cns (first send $fs)" | tee $O/verdict.log
[ $v = PASS ]
