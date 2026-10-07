#!/bin/bash
# run_vm_tiles.sh <out dir>: r19 VM quadrant tiles joined vs the monolithic hfd_vm (tb_vm_tiles.sv).  Mode 1 seeds 1-3
# (transaction hashes MATCH), mode 2 seed 1 (check_vm_tiles.py: one constant latency per output bit), negative MUT_XBUS
# mode 1 (must FAIL).  Prints VM_TILES_BENCH PASS / FAIL and the per-path latency table.
O=${1:?}; mkdir -p $O; V=physical/hbm_accel_die_views; T=$V/vm/tiles
SR1=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
SRCS="$V/common/ot_hfd_oreg1.sv rtl/common/ot_fwd_link_stage.sv $SR1 $V/vm/rtl/ot_hbm_die_vm_multicast_root.sv $V/vm/rtl/hfd_vm.sv $T/ot_hfd_vm_slice.sv $T/ot_hfd_vm_root_x.sv $T/hfd_vm_sw.sv $T/hfd_vm_nw.sv $T/hfd_vm_se.sv $T/hfd_vm_ne.sv $T/tb_vm_tiles.sv"
b() { n=$1; shift; verilator --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-initial unique --top-module tb_vm_tiles "$@" -Mdir $O/$n.obj -o sim $SRCS > $O/$n.build 2>&1 || { echo "$n BUILD_FAILED"; grep -m5 -i error $O/$n.build; return 2; }; }
ok=1
for s in 1 2 3; do b m1s$s -DMODE=1 -DSEED=$s && (cd $O && ./m1s$s.obj/sim +verilator+seed+$s > m1s$s.log 2>&1); grep VM_TILES $O/m1s$s.log; grep -q "hash=MATCH" $O/m1s$s.log && ! grep -q "VM_TILES FAIL" $O/m1s$s.log || ok=0; done
b m2 -DMODE=2 -DSEED=1 && (cd $O && ./m2.obj/sim > m2.log 2>&1); python3 $T/check_vm_tiles.py $O/trace_ref.hex $O/trace_dut.hex > $O/m2.check; rc=$?; cat $O/m2.check | tail -25; [ $rc = 0 ] || ok=0
b neg -DMODE=1 -DSEED=1 -DMUT_XBUS && (cd $O && ./neg.obj/sim > neg.log 2>&1); grep VM_TILES $O/neg.log
grep -q "VM_TILES FAIL" $O/neg.log && echo "VM_TILES_NEG_DETECTED" || { echo "neg not detected"; ok=0; }
[ $ok = 1 ] && echo "VM_TILES_BENCH PASS" || echo "VM_TILES_BENCH FAIL"
