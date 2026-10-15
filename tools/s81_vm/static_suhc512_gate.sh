#!/bin/bash
set -eu
S=$1;O=$2;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
build(){ "$V" --binary --timing -O1 -Wno-fatal -j 2 --top-module tb_dsfd_vm_static512_suhc --Mdir "$O/obj_$1" -o tb ${2:-} "$S/dsfd_vm_static_fsr_bank8.sv" "$S/dsfd_vm_static_fsr_quartets.sv" "$S/dsfd_vm_static_suhc_fsr.sv" "$S/dsfd_vm_static_suhc_return_map.sv" "$S/dsfd_vm_static_write_capture128.sv" "$S/dsfd_vm_static_scatter_b8_out.sv" "$S/dsfd_vm_static_scatter_lane.sv" "$S/dsfd_vm_static_scatter.sv" "$S/dsfd_vm_static_bank128.sv" "$S/dsfd_vm_static_relay128.sv" "$S/dsfd_vm_static_relay128_b8.sv" "$S/dsfd_vm_static_relay128_b4.sv" "$S/dsfd_vm_static_slice128_suhc.sv" "$S/dsfd_vm_static_return.sv" "$S/dsfd_vm_static_return_bank8.sv" "$S/dsfd_vm_static_return_bank8_profiles.sv" "$S/dsfd_vm_static_return32_native_lanes.sv" "$S/dsfd_vm_static512_suhc.sv" "$S/ot_sram_1r1w_512x128_m4_r2c2.v" "$S/tb_dsfd_vm_static512_suhc.sv" > "$O/build_$1.log" 2>&1; }
build base & p1=$!;build tag +define+OT_VM_SUHC_FSR_MUT_TAG & p2=$!;build select +define+OT_VM_SUHC_MAP_MUT_SELECT & p3=$!;wait "$p1";wait "$p2";wait "$p3"
for c in base tag select;do "$O/obj_$c/tb" +TRACE="$S/read_map_inputs/L14.txt" > "$O/run_$c.log" 2>&1;head -2 "$O/run_$c.log";done
grep -qx PASS "$O/run_base.log";grep -qx FAIL "$O/run_tag.log";grep -qx FAIL "$O/run_select.log"
echo STATIC_SUHC512_GATE_PASS
