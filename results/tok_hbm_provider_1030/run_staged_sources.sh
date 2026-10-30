#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_provider ot_hbm_static_load_provider_quad.sv ot_hbm_static_load_addr_counter.sv ot_hbm_static_load_addr_map.sv ot_hbm_static_load_quad_vehicle.sv tb_provider.sv native_load_static.sv sram.v --Mdir obj >build.log 2>&1
./obj/Vtb_provider >baseline.log 2>&1
for arg in MUT_EPOCH MUT_RELEASE;do
 set +e
 ./obj/Vtb_provider +"$arg"=1 >"$arg.log" 2>&1
 rc=$?
 set -e
 test "$rc" -ne 0
 grep -q PROVIDER_FAULT "$arg.log"
done
cat baseline.log
echo PASS_GENUINE_PROVIDER_EPOCH_AND_RELEASE_CONTROLS
