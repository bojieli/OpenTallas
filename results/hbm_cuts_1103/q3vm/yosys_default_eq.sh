#!/bin/bash
# Default-parameter equivalence (CUT 0 / OHSEL 0 / vm_core WCUT 0 VOH 0 == main 3465966986): yosys equiv_make/simple/induct.
# Usage: yosys_default_eq.sh SRC_DIR (with gold/ and tree/ as staged by run_eq.sh's caller) OUT; runs in docker (memory cap).
set -u; S=$(cd $1 && pwd); O=$(mkdir -p $2 && cd $2 && pwd)
cat > $O/eq.ys <<Y
read_verilog -sv -DSYNTHESIS -DOT_COLL_ISSUER256_NATIVE32 /s/gold/ot_hgi_coll_slice_v7.sv /s/gold/ot_hgi_coll_static_vmwrite_roots_v6.sv /s/gold/ot_hgi_coll_static_vmwrite_roots_v6_physical.sv /s/gold/ot_hfd_coll_q3_vm_core.sv
hierarchy -top ot_hfd_coll_q3_vm_core
proc; flatten; opt_clean; rename ot_hfd_coll_q3_vm_core gold
design -stash gold
read_verilog -sv -DSYNTHESIS -DOT_COLL_ISSUER256_NATIVE32 /s/tree/rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_slice_v7.sv /s/tree/rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_vmwrite_roots_v6.sv /s/tree/rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_vmwrite_roots_v6_physical.sv /s/tree/rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hfd_coll_q3_vm_core.sv
hierarchy -top ot_hfd_coll_q3_vm_core
proc; flatten; opt_clean; rename ot_hfd_coll_q3_vm_core gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
async2sync
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status -assert
Y
docker run --rm --memory=24g --memory-swap=24g -v $S:/s:ro -v $O:/o openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /o/eq.log /o/eq.ys" ; echo "YOSYS_DEFAULT_EQ rc=$?"
grep -h "Found\|Proved\|unproven\|Equivalence successfully" $O/eq.log | tail -5
