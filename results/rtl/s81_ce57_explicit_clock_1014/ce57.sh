cd /srv/opentallas-scratch/claude/s81b-ce57/src
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
B="+define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 +define+OT_S81PH_COLL_OQPIPE +define+OT_S81PH_COLL_QPIPE +define+OT_S81PH_COLL_SPLIT +define+OT_S81PH_COLL_RSL +define+OT_S81PH_COLL_CR +define+OT_S81PH_LANE_CR +define+OT_S81PH_COLL_PULL +define+OT_S81PH_COLL_TREP +define+OT_S81PH_COLL_CEH +define+OT_S81PH_COLL_CES_SPLIT +define+OT_S81PH_COLL_CES_ENTRIES"
bash rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh ../out exact $B > ../exact.rc 2>&1; echo "exact rc=$?" >> ../exact.rc &
bash rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh ../out mut_cesx $B +define+OT_S81PH_MUT_CESX > ../mut_cesx.rc 2>&1; echo "cesx rc=$?" >> ../mut_cesx.rc &
bash rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh ../out mut_cesl $B +define+OT_S81PH_MUT_CESL > ../mut_cesl.rc 2>&1; echo "cesl rc=$?" >> ../mut_cesl.rc &
bash rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh ../out mut_lock $B +define+OT_S81PH_MUT_LOCKSTEP +define+OT_S81PH_LOCKSTEP_NOASSERT > ../mut_lock.rc 2>&1; echo "lock rc=$?" >> ../mut_lock.rc &
wait; cat ../*.rc
