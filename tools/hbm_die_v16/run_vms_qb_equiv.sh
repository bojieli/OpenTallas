#!/usr/bin/env bash
# HBM-B-RTL1 2026-10-17 (plan (b) d4g): lockstep of the hoisted VM slice (glue + 8 die-level q0_faces banks) against the
# full-slice reference, every output on every edge, 3000 random edges.  Q = SW runs the d4f hoist bench
# (vms_hoist_equiv.py, the d4f behaviour); Q = SE / NE runs the plan (b) E-quadrant slices WITH the SM client side
# (vms_qb_equiv.py: SW shape, sid 1 / 3, NC 1).  pos must print "<TAG> <Q> PASS", mut (bank 0/1 rslot swap) must print
# "<TAG> <Q> FAIL checks=N errors=M>0".      run_vms_qb_equiv.sh Q pos|mut OUT
set -uo pipefail
q=${1:?quadrant}; m=${2:?pos|mut}; OUT=$(realpath -m "${3:?out}"); mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/hbm_accel/generic/vm/static
src=($S/hfd_hgi_vms_static.sv $S/hfd_hgi_vms_static_glue.sv $S/hfd_hgi_vms_static_core.sv $S/hfd_hgi_vms_static_qb.sv $S/ot_vms_slice_static.sv
     $S/ot_vms_bank_native_physical.sv $S/ot_vms_hub_static.sv $S/ot_vms_rstop_static.sv $S/ot_vms_rcl_static.sv $S/ot_vms_status_static.sv
     $S/ot_vms_bank_static.sv $S/ot_vms_bank_strap_physical.sv $S/ot_vms_ce_counter_pipe.sv $S/wq_merge/hfd_vms_wq2_merge.sv $S/physical/*.sv
     $(ls $S/ot_vms_bank_static_*.sv) $S/faces_q0/hfd_vms_bank_native_q0_faces.sv $S/faces_q0/ot_vms_bank_q0_faces_core.sv
     $S/faces_q0/ot_vms_bank_q0_faces_body.sv rtl/lib/ot_rst_relay.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
X=; [ "$m" = mut ] && X=--mut
if [ "$q" = SW ] || [ "$q" = NW ]; then T=vms_hoist_equiv; TAG=VMS_HOIST_EQUIV; else T=vms_qb_equiv; TAG=VMS_QB_EQUIV; fi
comp=$([ $T = vms_hoist_equiv ] && echo vms_hoist_comp_$q.sv || echo vms_hoist_comp_$q.sv)
python3 tools/hbm_die_v16/$T.py --layer tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json --quadrant $q --out "$OUT/$q$m" $X > "$OUT/$q$m.gen.log" 2>&1 || { cat "$OUT/$q$m.gen.log"; echo "$TAG $q GENFAIL"; exit 1; }
"$V" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_vms_hoist -Mdir "$OUT/$q$m/obj" \
  "${src[@]}" "$OUT/$q$m/$comp" "$OUT/$q$m/tb_vms_hoist.sv" > "$OUT/$q$m.build.log" 2>&1 || { grep -m5 %Error "$OUT/$q$m.build.log"; echo "$TAG $q BUILDFAIL"; exit 1; }
"$OUT/$q$m/obj/Vtb_vms_hoist" 2>&1 | grep -E "$TAG|MISMATCH" | tail -3
rm -rf "$OUT/$q$m/obj"
