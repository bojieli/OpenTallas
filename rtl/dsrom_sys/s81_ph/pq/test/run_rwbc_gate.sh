#!/bin/bash
# exact gate of ot_s81_pq_rwbc (count-only PQ return leaf) vs the RWB's ga / q2f.  run_rwbc_gate.sh <out> [defines]
# exit 0 iff RWBC_GATE PASS.  Mutant: OT_S81_PQ_RWBC_MUT_GA must FAIL.
set -u
O=$1; D=${2:-}; mkdir -p $O
V=${OT_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
$V --binary -O2 -Wno-fatal -Wno-lint -Wno-style -j 8 --top-module tb_ot_s81_pq_rwbc $D --Mdir $O/obj \
  rtl/dsrom_sys/s81_ph/pq/test/tb_ot_s81_pq_rwbc.sv rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_rwbc.sv rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_rwb.sv \
  rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv > $O/build.log 2>&1 || { echo BUILD_FAIL; grep -m5 -i error $O/build.log; exit 2; }
$O/obj/Vtb_ot_s81_pq_rwbc > $O/run.log 2>&1
grep -E "RWBC" $O/run.log | tail -4
grep -q "RWBC_GATE PASS" $O/run.log
