#!/usr/bin/env bash
# S81-KITS-RTLC ruling (b) benches: bk_sel (die path, VD_PK=1) base / landed lp / mutant; legacy VD_PK=0 parents compile+run
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
W=/srv/opentallas-scratch/claude/wt/s81-kits-1024r-nodes; O=/srv/opentallas-scratch2/claude/rtlc2/bk; rm -rf $O; mkdir -p $O; cd $W
S=rtl/dsrom_sys/s81_dv/unit/bk/test/run_bk_bench.sh
sed 's/+define+OT_DSDV_BK=\$MUT /+define+OT_DSDV_BK=$MUT +define+OT_RTLC_MUT_BKVD /' $S > $O/run_bk_bench_mut.sh
grep -c OT_RTLC_MUT_BKVD $O/run_bk_bench_mut.sh > $O/mutdefs.txt
(JOBS=8 bash $S sel $O/base 0 > $O/base.txt 2>&1; echo "rc=$?" >> $O/base.txt) &
(LP=1 JOBS=8 bash $S sel $O/lp 0 > $O/lp.txt 2>&1; echo "rc=$?" >> $O/lp.txt) &
(JOBS=8 bash $O/run_bk_bench_mut.sh sel $O/mut 0 base odd > $O/mut.txt 2>&1; echo "rc=$?" >> $O/mut.txt) &
(JOBS=8 bash $S col $O/col 0 gold1 > $O/col.txt 2>&1; echo "rc=$?" >> $O/col.txt) &
(SIM=verilator MUTS=0 VL_JOBS=8 LP_ROOT=$W bash rtl/dsrom_sys/s81_dv/unit/bk/plana/lp/dsdv_bk_sel_pa_lp_bench.sh $O/pa > $O/pa.txt 2>&1; echo "rc=$?" >> $O/pa.txt) &
wait
