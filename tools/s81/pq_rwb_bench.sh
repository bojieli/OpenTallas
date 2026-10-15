#!/bin/bash
# Exact bench of the S81 PQ RWB masters vs the reference T_RET group.  usage: pq_rwb_bench.sh WORKDIR NR(10|11) [MUT]
# MUT: GA (row count drops the last region) | DATA (w_data byte order reversed) | none
set -e
W=$1; NR=$2; MUT=${3:-none}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
V=${OT_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=$ROOT/physical/s81_pq_hier/pinned/rtl
mkdir -p $W
D=""; [ "$NR" = 11 ] && D="+define+NR11"
M=""; [ "$MUT" = GA ] && M="+define+OT_S81_PQ_RWB_MUT_GA"; [ "$MUT" = DATA ] && M="+define+OT_S81_PQ_RWB_MUT_DATA"
$V --binary -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 --top-module tb_s81_pq_rwb \
  -Mdir $W/obj $D $M $P/ot_rst_relay.sv $P/hdc/ot_hdc_delay.sv $P/v41rom/ot_v41_kreg.sv $P/common/ot_prefix.sv \
  $P/v41die/ot_v41_pqc_tiles.sv $ROOT/rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_rwb.sv $ROOT/rtl/test/dsrom_sys/tb_s81_pq_rwb.sv \
  > $W/build.log 2>&1 || { tail -30 $W/build.log; exit 2; }
$W/obj/Vtb_s81_pq_rwb | tee $W/run.log | tail -12
grep -q "^RWB_EXACT PASS" $W/run.log
