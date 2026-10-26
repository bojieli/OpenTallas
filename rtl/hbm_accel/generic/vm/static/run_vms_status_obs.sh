#!/usr/bin/env bash
# HBM-BIND P-VMST-OBS (2026-10-26): vm_status4 -> obs_C composition bench (B2 die top); positive PASS, two mutants FAIL
# (status4 drops quadrant 1 from the ce sum; obs leaf drops obs[N-1] = proto_fault).   run_vms_status_obs.sh OUT
set -uo pipefail
out=${1:?out}; mkdir -p "$out"; d=rtl/hbm_accel/generic/vm/static; fail=0
src=("$d/ot_vms_status4_static.sv" physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/die_glue/ot_hbm_obs_leaf.sv rtl/lib/ot_rst_relay.sv "$d/tb_vms_status_obs.sv")
for m in pos mut_status mut_obs; do
 def=(); [ $m = mut_status ] && def=(-DOT_VMS_STATUS_MUT); [ $m = mut_obs ] && def=(-DOT_OBS_MUT)
 iverilog -g2012 "${def[@]}" -o "$out/s_$m" "${src[@]}" || { echo "BUILD_FAIL $m"; exit 2; }
 vvp "$out/s_$m" > "$out/$m.log"; r=$(grep -o 'VMS_STATUS_OBS [A-Z]* checks=[0-9]* errors=[0-9]*' "$out/$m.log"); echo "$m $r"
 if [ $m = pos ]; then echo "$r" | grep -q ' PASS ' || fail=1; else echo "$r" | grep -Eq ' FAIL checks=[0-9]+ errors=[1-9]' || fail=1; fi
done
[ $fail = 0 ] && echo VMS_STATUS_OBS_GATE PASS || { echo VMS_STATUS_OBS_GATE FAIL; exit 1; }
