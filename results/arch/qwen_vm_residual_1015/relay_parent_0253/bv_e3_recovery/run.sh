#!/bin/bash
set -eu
for m in 0 1_early; do
 "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 4 -O1 -Wno-fatal --top-module tb --Mdir "obj$m" "m$m.sv" > "m$m.build.log" 2>&1
 set +e
 "obj$m/Vtb" > "m$m.run.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "m$m.exit"
 sha256sum "obj$m/Vtb" "m$m.sv" > "m$m.sha256"
 if [ "$m" = 0 ]; then test "$rc" = 0; grep -q 'PASS exact E3 all43184bits checks129552000' "m$m.run.log"; else test "$rc" != 0; grep -q 'FAIL bw_data cycle0' "m$m.run.log"; fi
done
printf '%s\n' 'PASS recovered immutable E3 positive and observed hardware negative'
