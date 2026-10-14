#!/bin/bash
# run_vm_cp.sh <out dir> [verilator]: [vm8cp] channel-plan VM (hfd_vm_cp = 25 tiles of make_vm_cp.py) vs the monolithic
# hfd_vm (tb_vm_cp.sv).  Gates (all must hold for VM_CP_BENCH PASS):
#   lint   every tile top elaborates (verilator --lint-only)
#   mode 1 seeds 1-3 transaction hashes MATCH (write ACK owners, publishes at all four x faces, fault/drained)
#   mode 2 every output bit at ONE constant latency vs the monolithic (check_vm_tiles.py; prints the per-path table)
#   mode 3 root write / read ports ONE depth from their die pins; monolithic wr SKEWED detected
#   negatives MUT_XBUS (SE slice wd bits 10/11) and MUT_RELAY (xSE tap bits 10/11 in the E fork) must FAIL mode 1
# vm_env_body_cp.svh: the r19 env hashed xSW/xNE[2078:2016] (11 bits past the 2,068-bit port); Verilator returned 0x000 in one
# env and 0x7ff in the other on identical in-range data. The copy keeps that chunk in range ([2062:2016]) for BOTH designs.
O=${1:?}; VL=${2:-verilator}; mkdir -p $O; V=physical/hbm_accel_die_views; T=$V/vm/tiles; C=$V/vm/cp
SR1=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
BASE="$V/common/ot_hfd_oreg1.sv rtl/common/ot_fwd_link_stage.sv $SR1 $V/vm/rtl/ot_hbm_die_vm_multicast_root.sv $V/vm/rtl/hfd_vm.sv $T/ot_hfd_vm_slice.sv $T/ot_hfd_vm_root_x.sv $T/ot_hfd_vm_root_p.sv"
TILES=$(ls $C/rtl/vm_cp_*.sv | tr '\n' ' ')
ok=1; $VL --version
for f in $TILES; do m=$(basename $f .sv)
  $VL --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module $m rtl/common/ot_fwd_link_stage.sv $SR1 $T/ot_hfd_vm_slice.sv $T/ot_hfd_vm_root_p.sv $f > $O/lint_$m.log 2>&1 || { echo "lint $m FAIL"; ok=0; }
done
# VM_CP_MUT=<XBUS|RELAY>: build EVERY mode with that mutant (the loop's expect=fail bench: mode 1 must DIFF -> FAIL)
MUTD=${VM_CP_MUT:+-DMUT_$VM_CP_MUT}
b() { n=$1; shift; $VL $MUTD -I$C -I$T --binary --timing -j 16 --unroll-count 8192 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-initial unique --top-module tb_vm_tiles "$@" -Mdir $O/$n.obj -o sim $BASE $TILES $C/hfd_vm_cp.sv $C/tb_vm_cp.sv > $O/$n.build 2>&1 || { echo "$n BUILD_FAILED"; grep -m5 -i error $O/$n.build; return 2; }; }
for s in 1 2 3; do b m1s$s -DMODE=1 -DSEED=$s && (cd $O && ./m1s$s.obj/sim +verilator+seed+$s > m1s$s.log 2>&1); grep -E "VM_TILES|VM_CP" $O/m1s$s.log | tail -2; grep -q "hash=MATCH" $O/m1s$s.log && ! grep -qE "VM_TILES FAIL|not aligned" $O/m1s$s.log || ok=0; done
mkdir -p $O/m2; b m2 -DMODE=2 -DSEED=1 && (cd $O/m2 && ../m2.obj/sim > m2.log 2>&1)
python3 $T/check_vm_tiles.py $O/m2/trace_ref.hex $O/m2/trace_dut.hex > $O/m2.check; rc=$?; tail -25 $O/m2.check; [ $rc = 0 ] || ok=0
b m3 -DMODE=3 -DSEED=1 && (cd $O && ./m3.obj/sim > m3.log 2>&1); grep "VM_PORT_DEPTH" $O/m3.log
grep -Eq "VM_PORT_DEPTH trace_dut.hex wr= *ONE_DEPTH rd= *ONE_DEPTH" $O/m3.log || { echo "cp port depth not one-depth"; ok=0; }
grep -Eq "VM_PORT_DEPTH trace_ref.hex wr= *SKEWED" $O/m3.log && echo "VM_PORT_DEPTH_NEG_DETECTED (monolithic wr skew)" || { echo "port-depth negative not detected"; ok=0; }
for m in XBUS RELAY; do
  b neg_$m -DMODE=1 -DSEED=1 -DMUT_$m && (cd $O && ./neg_$m.obj/sim > neg_$m.log 2>&1); grep VM_TILES $O/neg_$m.log
  grep -q "VM_TILES FAIL" $O/neg_$m.log && echo "VM_CP_NEG_${m}_DETECTED" || { echo "neg $m not detected"; ok=0; }
done
if [ $ok = 1 ]; then echo "VM_CP_BENCH PASS"; else echo "VM_CP_BENCH FAIL"; exit 1; fi
