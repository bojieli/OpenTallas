#!/bin/bash
set -euo pipefail
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version
for m in 0 1;do
 "$V" --binary --timing -Wno-fatal -j 8 --top-module tb -GMUT=$m --Mdir obj$m rtl/test/landed_parent/tb_su_ring_fan32.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv > build$m.log 2>&1
 set +e
 ./obj$m/Vtb > proof$m.log 2>&1
 rc=$?
 set -e
 cat proof$m.log
 if [ "$m" = 0 ];then test "$rc" = 0;grep -q 'SU_RING_FAN32_PROOF PASS' proof$m.log;else test "$rc" != 0;grep -q RING_FAN32_MISMATCH proof$m.log;fi
done
