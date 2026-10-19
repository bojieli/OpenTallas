#!/usr/bin/env bash
# OWNERS-HBM/VM-GLUE 2026-10-18: VM hub-glue TILE top (hfd_hgi_vms_glue_{sw,e,nw}_t) + 8 die-level q0_faces banks
# [+ NW merges] == full-slice reference, every output on every edge, 3000 random edges (vms_glue_tile_equiv.py over
# the vms_hoist_equiv / vms_qb_equiv compositions).  pos must print "<TAG> <Q> PASS checks=N errors=0"; mut (bank: bank
# 0/1 rslot swap; sid: E strap = the other E quadrant's sid) must print "<TAG> <Q> FAIL checks=N errors=M>0".
# Exit status 0 only on a counted PASS.
#   run_vms_glue_tile_equiv.sh Q pos|bank|sid OUT
set -uo pipefail
q=${1:?quadrant}; m=${2:?pos|bank|sid}; OUT=$(realpath -m "${3:?out}"); mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/hbm_accel/generic/vm/static
src=($S/hfd_hgi_vms_static.sv $S/hfd_hgi_vms_static_glue.sv $S/hfd_hgi_vms_static_core.sv $S/hfd_hgi_vms_static_qb.sv
     $S/hfd_hgi_vms_glue_tiles.sv $S/hfd_hgi_vms_glue_tiles_flat.sv $S/ot_vms_slice_static.sv
     $S/ot_vms_bank_native_physical.sv $S/ot_vms_hub_static.sv $S/ot_vms_rstop_static.sv $S/ot_vms_rcl_static.sv $S/ot_vms_status_static.sv
     $S/ot_vms_bank_static.sv $S/ot_vms_bank_strap_physical.sv $S/ot_vms_ce_counter_pipe.sv $S/wq_merge/hfd_vms_wq2_merge.sv $S/physical/*.sv
     $(ls $S/ot_vms_bank_static_*.sv) $S/faces_q0/hfd_vms_bank_native_q0_faces.sv $S/faces_q0/ot_vms_bank_q0_faces_core.sv
     $S/faces_q0/ot_vms_bank_q0_faces_body.sv rtl/lib/ot_rst_relay.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
case $q in SW|NW) TAG=VMS_HOIST_EQUIV;; *) TAG=VMS_QB_EQUIV;; esac
X=; [ "$m" != pos ] && X="--mut $m"
D="$OUT/$q$m"
python3 tools/hbm_die_v16/vms_glue_tile_equiv.py --quadrant $q --out "$D" $X > "$D.gen.log" 2>&1 || { cat "$D.gen.log"; echo "$TAG $q GENFAIL"; exit 1; }
grep VMS_GLUE_TILE_TB "$D.gen.log"
"$V" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_vms_hoist -Mdir "$D/obj" \
  "${src[@]}" "$D/vms_hoist_comp_$q.sv" "$D/tb_vms_hoist.sv" > "$D.build.log" 2>&1 || { grep -m5 %Error "$D.build.log"; echo "$TAG $q BUILDFAIL"; exit 1; }
"$D/obj/Vtb_vms_hoist" > "$D.sim.log" 2>&1
rm -rf "$D/obj"
grep -E "$TAG|MISMATCH" "$D.sim.log" | tail -4
grep -Eq "^$TAG $q PASS checks=[1-9][0-9]* errors=0$" "$D.sim.log"   # exit 0 only on a counted PASS (mutants: non-zero)
