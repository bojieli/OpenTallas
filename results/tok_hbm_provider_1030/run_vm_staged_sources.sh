#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -j 8 --output-split 10000 -Wno-fatal --top-module tb_vm_provider ot_hgi_dma_back_cp_collar.sv ot_static_cmd_target.sv ot_hbm_static_load_cp_provider_quad.sv ot_hbm_static_load_provider_quad.sv ot_hbm_static_load_addr_counter.sv ot_hbm_static_load_addr_map.sv ot_hbm_static_load_quad_vehicle.sv ot_hbm_static_load_vm_commit_guard.sv ot_hbm_static_load_vm_dq_demux.sv hfd_vms_bank_native_q0_faces.sv ot_vms_bank_q0_faces_core.sv ot_vms_bank_q0_faces_body.sv ot_vms_ce_counter_pipe.sv tb_vm_provider.sv native_load_static.sv sram.v ot_sram_1r1w_1024x256_m2_r2c2.v --Mdir obj >build.log 2>&1
./obj/Vtb_vm_provider >baseline.log 2>&1
for arg in MUT_SLOT MUT_BANK MUT_LATE;do
 set +e
 ./obj/Vtb_vm_provider +"$arg"=1 >"$arg.log" 2>&1
 rc=$?
 set -e
 test "$rc" -ne 0
 grep -q VM_PROVIDER_FAULT "$arg.log"
done
cat baseline.log
echo PASS_NATIVE_VM_PROVIDER_AND_CONTROLS
