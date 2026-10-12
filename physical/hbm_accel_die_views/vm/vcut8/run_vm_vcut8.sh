#!/bin/bash
# run_vm_vcut8.sh <out dir> [verilator]: the 8 vertical-cut VM halves joined (hfd_vm_<q>_jv) vs the monolithic hfd_vm (tb_vm_vcut8.sv
# = tiles/tb_vm_tiles.sv with `VCUT8), and vs the r22 4-tile version.  Gates (all must hold for VM_VCUT8_BENCH PASS):
#   lint   every sub-tile top elaborates clean (verilator --lint-only, warnings non-fatal as in the tiles bench)
#   mode 1 seeds 1-3: transaction hashes MATCH the monolithic (write ACK owners, publishes at all four x faces, fault/drained)
#   mode 2 every output bit at ONE constant latency vs the monolithic (check_vm_tiles.py) AND vs the 4-tile (the split's
#          per-path cycle cost, printed as the 8-vs-4 latency table)
#   mode 3 the root write and read ports stay ONE depth from their die pins (vm_wr_skew_finding.md); monolithic wr SKEWED
#   negatives: MUT_XBUS (SW -> SE wr bus bits 10/11 swapped) and MUT_SEAM (SE seam tap bits 10/11 swapped) must FAIL mode 1
O=${1:?}; VL=${2:-verilator}; mkdir -p $O; V=physical/hbm_accel_die_views; T=$V/vm/tiles; S=$V/vm/vcut8
SR1=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
BASE="$V/common/ot_hfd_oreg1.sv $V/vm/vcut8/ot_hfd_oreg_fc.sv rtl/common/ot_fwd_link_stage.sv $SR1 $V/vm/rtl/ot_hbm_die_vm_multicast_root.sv $V/vm/rtl/hfd_vm.sv $T/ot_hfd_vm_slice.sv $T/ot_hfd_vm_root_x.sv"
HALVES=""; for q in sw nw se ne; do HALVES="$HALVES $S/hfd_vm_${q}_w.sv $S/hfd_vm_${q}_e.sv $S/hfd_vm_${q}_jv.sv"; done
Q4="$T/hfd_vm_sw.sv $T/hfd_vm_nw.sv $T/hfd_vm_se.sv $T/hfd_vm_ne.sv"
ok=1
for q in sw nw se ne; do for h in w e; do
  $VL --lint-only --unroll-count 8192 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module hfd_vm_${q}_${h} $V/common/ot_hfd_oreg1.sv $V/vm/vcut8/ot_hfd_oreg_fc.sv rtl/common/ot_fwd_link_stage.sv $SR1 $T/ot_hfd_vm_slice.sv $T/ot_hfd_vm_root_x.sv $S/hfd_vm_${q}_${h}.sv > $O/lint_${q}_${h}.log 2>&1 && echo "LINT hfd_vm_${q}_${h} ok" || { echo "LINT hfd_vm_${q}_${h} FAIL"; grep -m5 -i error $O/lint_${q}_${h}.log; ok=0; }
done; done
b() { n=$1; tb=$2; srcs=$3; shift 3; $VL -I$T --binary --timing -j 16 --unroll-count 8192 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-initial unique --top-module tb_vm_tiles "$@" -Mdir $O/$n.obj -o sim $BASE $srcs $tb > $O/$n.build 2>&1 || { echo "$n BUILD_FAILED"; grep -m5 -i error $O/$n.build; return 2; }; }
for s in 1 2 3; do b m1s$s $S/tb_vm_vcut8.sv "$HALVES" -DVCUT8 -DMODE=1 -DSEED=$s && (cd $O && ./m1s$s.obj/sim +verilator+seed+$s > m1s$s.log 2>&1); grep VM_TILES $O/m1s$s.log; grep -q "hash=MATCH" $O/m1s$s.log && ! grep -q "VM_TILES FAIL" $O/m1s$s.log || ok=0; done
mkdir -p $O/m2_8 $O/m2_4
b m2_8 $S/tb_vm_vcut8.sv "$HALVES" -DVCUT8 -DMODE=2 -DSEED=1 && (cd $O/m2_8 && ../m2_8.obj/sim > m2.log 2>&1)
b m2_4 $T/tb_vm_tiles.sv "$Q4" -DMODE=2 -DSEED=1 && (cd $O/m2_4 && ../m2_4.obj/sim > m2.log 2>&1)
python3 $T/check_vm_tiles.py $O/m2_8/trace_ref.hex $O/m2_8/trace_dut.hex > $O/m2_8vsmono.check; rc=$?; echo "== 8-way vs monolithic"; tail -3 $O/m2_8vsmono.check; [ $rc = 0 ] || ok=0
cmp -s $O/m2_8/trace_ref.hex $O/m2_4/trace_ref.hex || { echo "monolithic traces differ between the 8 and 4 runs (stimulus mismatch)"; ok=0; }
python3 $T/check_vm_tiles.py $O/m2_4/trace_dut.hex $O/m2_8/trace_dut.hex > $O/m2_8vs4.check; rc=$?; echo "== 8-way vs 4-tile (latency = added cycles per path)"; cat $O/m2_8vs4.check; [ $rc = 0 ] || ok=0
b m3 $S/tb_vm_vcut8.sv "$HALVES" -DVCUT8 -DMODE=3 -DSEED=1 && (cd $O && ./m3.obj/sim > m3.log 2>&1); grep "VM_PORT_DEPTH" $O/m3.log
grep -Eq "VM_PORT_DEPTH trace_dut.hex wr= *ONE_DEPTH rd= *ONE_DEPTH" $O/m3.log || { echo "vcut8 port depth not one-depth"; ok=0; }
grep -Eq "VM_PORT_DEPTH trace_ref.hex wr= *SKEWED" $O/m3.log && echo "VM_PORT_DEPTH_NEG_DETECTED (monolithic wr skew)" || { echo "port-depth negative not detected"; ok=0; }
for m in XBUS SEAM SEATP; do   # SEATP: the root LOAD skips the seat load (must FAIL mode 1)
  b neg_$m $S/tb_vm_vcut8.sv "$HALVES" -DVCUT8 -DMODE=1 -DSEED=1 -DMUT_$m && (cd $O && ./neg_$m.obj/sim > neg_$m.log 2>&1); grep VM_TILES $O/neg_$m.log
  grep -q "VM_TILES FAIL" $O/neg_$m.log && echo "VM_VCUT8_NEG_${m}_DETECTED" || { echo "neg $m not detected"; ok=0; }
done
[ $ok = 1 ] && echo "VM_VCUT8_BENCH PASS" || echo "VM_VCUT8_BENCH FAIL"
