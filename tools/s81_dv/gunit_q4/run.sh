#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
R=$PWD
O=$R/out
mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version | tee "$O/version.txt"
F=(rtl/hdc/v41/ot_hdc_sinkhorn_p.sv rtl/hdc/v41/ot_hdc_skp_predecode.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv tools/s81_dv/gunit_q4/tb_q4.sv)
sha256sum "${F[@]}" > "$O/sources.sha256"
for m in 0 1; do
 "$V" --binary --timing -j 12 -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-TIMESCALEMOD "+define+Q4_MUT=$m" --top-module tb_q4 --Mdir "$O/obj$m" -o tb "${F[@]}" -CFLAGS -O1 > "$O/build$m.log" 2>&1
 if [ "$m" = 0 ]; then
  "$O/obj0/tb" +N=192 > "$O/positive.log" 2>&1
  grep '^Q4 PASS' "$O/positive.log"
  for age in 602 641 643; do
   set +e; "$O/obj0/tb" +N=1 +expect_age=$age > "$O/age${age}.log" 2>&1; rc=$?; set -e
   [ "$rc" != 0 ]; grep 'Q4 FAIL' "$O/age${age}.log" | head -1
  done
 else
  set +e; "$O/obj1/tb" +N=8 > "$O/mutant_predicate.log" 2>&1; rc=$?; set -e
  [ "$rc" != 0 ]; grep 'Q4 FAIL numerical' "$O/mutant_predicate.log" | head -1
 fi
done
echo 'Q4_COMPONENT_TERMINAL PASS'
