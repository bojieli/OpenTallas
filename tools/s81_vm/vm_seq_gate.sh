#!/bin/bash
# vm_seq_gate.sh <src root> <out dir> [seeds]: exact gate of the S81 VM sequencer engine dsfd_vm_seq on the real VM master
# dsfd_sp_vm_m (bench rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_seq.sv).  PASS iff every seed of the base build PASSes and every
# mutant (OT_VMSEQ_MUT_EARLYCR / _ORDER / _NOFENCE) FAILs on at least one seed.  Prints VM_SEQ_GATE PASS|FAIL.
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
S=$1; O=$2; SEEDS=${3:-"1 2 3"}; mkdir -p $O
F="$S/rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv $S/rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv $S/rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv
   $S/rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgl.sv $S/rtl/dsrom_sys/mtp/dsfd_vm_wfc_ep.sv $S/rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv
   $S/rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv $S/rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv
   $S/rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv $S/rtl/lib/ot_async_fifo.sv $S/rtl/lib/ot_reset_sync.sv
   $S/rtl/common/ot_ratio_cdc_fifo.sv
   $S/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
   $S/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
   $S/rtl/dsrom_sys/s81_ph/vm/dsfd_vm_seq.sv $S/rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_seq.sv"
b() { verilator --binary --timing -O1 -Wno-UNOPTFLAT -Wno-fatal -Wno-lint -Wno-style -j 4 --top-module tb_dsfd_vm_seq \
      -I$S/rtl/dsrom_sys/s81_ph/vm --Mdir $O/obj_$1 -o tb $2 $F > $O/build_$1.log 2>&1 || { echo "BUILD_FAIL $1"; grep -m8 -i error $O/build_$1.log; return 2; }; }
b base "" & b earlycr "+define+OT_VMSEQ_MUT_EARLYCR" & b order "+define+OT_VMSEQ_MUT_ORDER" & b nofence "+define+OT_VMSEQ_MUT_NOFENCE" & wait
v=PASS
for t in base earlycr order nofence; do
  [ -x $O/obj_$t/tb ] || { echo "VM_SEQ_GATE FAIL (build $t)"; exit 2; }
  nf=0
  for s in $SEEDS; do
    (cd $O && timeout 3000 ./obj_$t/tb +SEED=$s > run_${t}_s$s.log 2>&1)
    r=$(grep -E "^(PASS|FAIL)$" $O/run_${t}_s$s.log | tail -1)
    if [ -z "$r" ] && grep -qE '^FAIL|Assertion failed.*SPVM EARLY_READ' $O/run_${t}_s$s.log; then r=FAIL; fi
    if [ -z "$r" ]; then echo "HARNESS_FAIL $t seed $s"; v=FAIL; fi
    echo "$t seed $s: ${r:-NONE} | $(grep -m1 ^RESULT $O/run_${t}_s$s.log)"
    [ "$r" = PASS ] || nf=$((nf+1))
  done
  if [ $t = base ]; then [ $nf -eq 0 ] || v=FAIL; else [ $nf -gt 0 ] || { v=FAIL; echo "MUTANT $t NOT OBSERVED"; }; fi
done
echo "VM_SEQ_GATE $v"
[ $v = PASS ]
