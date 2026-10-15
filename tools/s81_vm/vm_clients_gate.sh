#!/bin/bash
# vm_seq_gate.sh <src root> <out dir> [seeds]: exact gate of the S81 VM sequencer engine dsfd_vm_seq on the real VM master
# dsfd_sp_vm_m (bench rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_clients.sv).  PASS iff every seed of the base build PASSes and every
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
   $S/rtl/dsrom_sys/s81_ph/vm/dsfd_vm_write_ack.sv $S/rtl/dsrom_sys/s81_ph/vm/dsfd_vm_clients.sv $S/rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_clients.sv"
DEF=${4:-}
verilator $DEF --binary --timing -O1 -Wno-UNOPTFLAT -Wno-fatal -Wno-lint -Wno-style -j 8 --top-module tb_dsfd_vm_clients -I$S/rtl/dsrom_sys/s81_ph/vm --Mdir $O/obj -o tb $F > $O/build.log 2>&1 || exit 2
(cd $O && timeout 3000 ./obj/tb > run.log 2>&1)
cat $O/run.log
grep -qx PASS $O/run.log
