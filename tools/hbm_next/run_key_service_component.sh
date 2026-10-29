#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
O=$(mkdir -p "${1:?output}" && readlink -f "$1")
python3 "$R/tools/hbm_next/prepare_key_service_component.py" "$R" "$O"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd "$O"
verilator --binary --timing -Wno-fatal --top-module tb_key_service -j 4 --Mdir obj tb_key_service.sv -f sources.f > build.log 2>&1
./obj/Vtb_key_service > nominal.log 2>&1
for m in 1 2;do
 set +e
 ./obj/Vtb_key_service +MUT=$m > mutant$m.log 2>&1
 rc=$?
 set -e
 test "$rc" != 0
 grep -q KEY_SERVICE_ mutant$m.log
done
echo KEY_NATIVE_SERVICE_ALL_PASS
