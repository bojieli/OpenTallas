#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_cp_provider ot_hgi_dma_back_cp_collar.sv ot_static_cmd_target.sv ot_hbm_static_load_cp_provider_quad.sv ot_hbm_static_load_provider_quad.sv ot_hbm_static_load_addr_counter.sv ot_hbm_static_load_addr_map.sv ot_hbm_static_load_quad_vehicle.sv tb_cp_provider.sv native_load_static.sv sram.v --Mdir obj >build.log 2>&1
./obj/Vtb_cp_provider >baseline.log 2>&1
for arg in MUT_EPOCH MUT_DEADLINE;do
 set +e
 ./obj/Vtb_cp_provider +"$arg"=1 >"$arg.log" 2>&1
 rc=$?
 set -e
 test "$rc" -ne 0
 grep -q CP_PROVIDER_FAULT "$arg.log"
done
cat baseline.log
echo PASS_NATIVE_CP_PROVIDER_AND_CONTROLS
