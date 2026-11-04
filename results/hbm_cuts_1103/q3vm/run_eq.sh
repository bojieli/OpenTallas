#!/bin/bash
# DIE-HBM-61/CUTS q3_vm lockstep EQ + mutants. Usage: run_eq.sh REPO_TREE GOLD_DIR(out of git show at the base) OUT
set -u; R=$1; G=$2; O=$3; mkdir -p $O; cd $O
F="rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_slice_v7.sv rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_vmwrite_roots_v6.sv rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_vmwrite_roots_v6_physical.sv rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hfd_coll_q3_vm_core.sv"
: > gold.sv; for f in $F; do sed -E 's/\b(ot_h[a-z0-9_]+)/gold_\1/g' $G/$(basename $f) >> gold.sv; done
NEW=""; for f in $F; do NEW="$NEW $R/$f"; done
TB=$R/results/hbm_cuts_1103/q3vm/tb_q3vm_cut.sv
run(){ n=$1; shift; iverilog -g2012 -o $n.vvp "$@" gold.sv $NEW $TB >$n.build 2>&1 && vvp -n $n.vvp > $n.out 2>&1; grep -h "Q3VM_EQ" $n.out | grep -v MISMATCH | sed "s/^/$n: /" || echo "$n: BUILD/RUN ERROR"; }
run pass_w1v1 &
run pass_w0v1 -Ptb_q3vm_cut.WCUT=0 &
run pass_w1v0 -Ptb_q3vm_cut.VOH=0 &
run pass_w0v0 -Ptb_q3vm_cut.WCUT=0 -Ptb_q3vm_cut.VOH=0 &
run mut_w1_fault_late -Ptb_q3vm_cut.MUTW=3 &
run mut_w1_no_plus1 -Ptb_q3vm_cut.MUTW=6 &
run mut_w1_sched_ignored -Ptb_q3vm_cut.MUTW=2 &
run mut_voh_onehot -DOT_COLL_SLICE_MUT_ONEHOT &
wait
