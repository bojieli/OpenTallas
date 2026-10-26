#!/usr/bin/env bash
# H-SM 2200: single-quadrant, single-mode form of run_vms_hoist_equiv.sh (same composition, same tb, same sources) for
# closure-loop benches: pos must print "VMS_HOIST_EQUIV <Q> PASS", mut (bank 0/1 rslot swap) must print
# "VMS_HOIST_EQUIV <Q> FAIL checks=N errors=M>0".   run_vms_hoist_equiv_q.sh Q pos|mut OUT
set -uo pipefail
q=${1:?quadrant}; m=${2:?pos|mut}; OUT=$(realpath -m "${3:?out}"); mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/hbm_accel/generic/vm/static
src=($S/hfd_hgi_vms_static.sv $S/hfd_hgi_vms_static_glue.sv $S/hfd_hgi_vms_static_core.sv $S/ot_vms_slice_static.sv $S/ot_vms_bank_native_physical.sv
     $S/ot_vms_hub_static.sv $S/ot_vms_rstop_static.sv $S/ot_vms_rcl_static.sv $S/ot_vms_status_static.sv $S/ot_vms_bank_static.sv
     $S/ot_vms_bank_strap_physical.sv $S/ot_vms_ce_counter_pipe.sv $S/wq_merge/hfd_vms_wq2_merge.sv $S/physical/*.sv
     $(ls $S/ot_vms_bank_static_*.sv) rtl/lib/ot_rst_relay.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
X=; [ "$m" = mut ] && X=--mut
python3 tools/hbm_die_v16/vms_hoist_equiv.py --layer tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json --quadrant $q --out "$OUT/$q$m" $X > "$OUT/$q$m.gen.log" 2>&1 || { cat "$OUT/$q$m.gen.log"; echo "VMS_HOIST_EQUIV $q GENFAIL"; exit 1; }
"$V" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_vms_hoist -Mdir "$OUT/$q$m/obj" \
  "${src[@]}" "$OUT/$q$m/vms_hoist_comp_$q.sv" "$OUT/$q$m/tb_vms_hoist.sv" > "$OUT/$q$m.build.log" 2>&1 || { grep -m5 %Error "$OUT/$q$m.build.log"; echo "VMS_HOIST_EQUIV $q BUILDFAIL"; exit 1; }
"$OUT/$q$m/obj/Vtb_vms_hoist" 2>&1 | grep -E 'VMS_HOIST_EQUIV|MISMATCH' | tail -3
rm -rf "$OUT/$q$m/obj"
