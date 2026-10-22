#!/usr/bin/env bash
set -euo pipefail
V=${VERILATOR:-/opt/verilator-5.050/bin/verilator}
if [[ ! -x "$V" ]]; then V=$(command -v verilator); fi
"$V" --version | tee version.log
"$V" --version | grep -q '5.050'
for m in 0 1 2 3 4; do
 "$V" --binary --timing -j 8 -Wno-fatal --top-module bridge_tb -GMUTANT=$m --Mdir obj_$m private/qkd_host_axi_packet_rc.sv bridge_tb.sv > build_$m.log 2>&1
 set +e
 ./obj_$m/Vbridge_tb > witness_$m.log 2>&1
 rc=$?
 set -e
 if [[ $m == 0 ]]; then [[ $rc == 0 ]];grep -q 'PASS bridge component' witness_$m.log;
 else
  [[ $rc != 0 ]]
  case $m in 1) pattern=ACCEPTED_DMA_STUCK;;2) pattern=CSR_ERROR_ID;;3) pattern=POST_POISON_CSR_MUTATION;;4) pattern=OFFER_STABILITY;;esac
  grep -q "FAIL $pattern" witness_$m.log
 fi
 cat witness_$m.log
 done

"$V" --binary --timing -j 8 -Wno-fatal --top-module bridge_default_tb --Mdir obj_default private/qkd_host_axi_packet_rc.sv bridge_original.sv bridge_default_tb.sv > build_default.log 2>&1
./obj_default/Vbridge_default_tb > witness_default.log 2>&1
cat witness_default.log
