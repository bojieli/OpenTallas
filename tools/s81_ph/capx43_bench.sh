#!/bin/bash
# claude S-VM-CAPT-X8 2026-10-16: unit bench of the static capture data half (dsfd_capt_x8_x43.sv leaves under the
# dsfd_capt_x8_data_e wrapper) against the old dynamic dsfd_capt_x8_data (row_local queue + ratio FIFO) on the same
# stimulus (tb_dsfd_capt_x8_x43).  Mode 0: words/order/content equal, fixed new latency per sample index, no fault;
# modes 1..3: misaligned reset release must raise t_ho.  usage (source root): capx43_bench.sh <out> [defines...]
# verdict "CAPX43_BENCH PASS|FAIL"
set -u
OUT=$1; shift; d=''; for x in "$@"; do d="$d +define+$x"; done
mkdir -p $OUT
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN $d --top-module tb_dsfd_capt_x8_x43 \
  -Mdir $OUT/obj -o sim rtl/common/ot_ratio_cdc_fifo.sv rtl/hdc/ot_hdc_prefix.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_cap_tile.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_split.sv \
  rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_x8_x43.sv rtl/dsrom_sys/s81_ph/test/tb_dsfd_capt_x8_x43.sv > $OUT/build.log 2>&1 \
  || { tail -20 $OUT/build.log; echo "CAPX43_BENCH FAIL build"; exit 1; }
ok=1
for m in 0 1 2 3; do
  $OUT/obj/sim +mode=$m > $OUT/run_$m.log 2>&1
  grep -h '^LAT\|^COUNT\|^WORD\|^NEW\|^UNEXPECTED\|^TB_CAPX43' $OUT/run_$m.log
  grep -q "^TB_CAPX43 PASS mode $m" $OUT/run_$m.log || ok=0
done
[ $ok = 1 ] && echo "CAPX43_BENCH PASS" || echo "CAPX43_BENCH FAIL"
