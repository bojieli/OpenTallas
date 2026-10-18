#!/usr/bin/env bash
# H-NETLIST 2200: VM bank hoist equivalence (SW + NW): original wrapper (STRAP_BANKS=1[, Q2_MERGE=1]) vs the layer's
# glue + bank (+ merge) composition, every output every edge; mutant (bank 0/1 rslot swapped) must FAIL.
#   run_vms_hoist_equiv.sh OUT
set -uo pipefail
OUT=$(realpath -m "${1:?out}"); mkdir -p "$OUT"; fail=0
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/hbm_accel/generic/vm/static
src=($S/hfd_hgi_vms_static.sv $S/hfd_hgi_vms_static_glue.sv $S/hfd_hgi_vms_static_core.sv $S/ot_vms_slice_static.sv $S/ot_vms_bank_native_physical.sv
     $S/ot_vms_hub_static.sv $S/ot_vms_rstop_static.sv $S/ot_vms_rcl_static.sv $S/ot_vms_status_static.sv $S/ot_vms_bank_static.sv
     $S/ot_vms_bank_strap_physical.sv $S/ot_vms_ce_counter_pipe.sv $S/wq_merge/hfd_vms_wq2_merge.sv $S/physical/*.sv $S/faces_q0/*.sv
     $(ls $S/ot_vms_bank_static_*.sv | grep -v tb_) rtl/lib/ot_rst_relay.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
sha256sum "${src[@]}" tools/hbm_die_v16/gen_vms_hoist.py tools/hbm_die_v16/vms_hoist_equiv.py tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json > "$OUT/sources.sha256"
for q in SW NW SE NE; do for m in pos mut; do
  X=; [ $m = mut ] && X=--mut
  python3 tools/hbm_die_v16/vms_hoist_equiv.py --layer tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json --quadrant $q --out "$OUT/$q$m" $X > "$OUT/$q$m.gen.log" || { cat "$OUT/$q$m.gen.log"; fail=1; continue; }
  "$V" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_vms_hoist -Mdir "$OUT/$q$m/obj" \
    "${src[@]}" "$OUT/$q$m/vms_hoist_comp_$q.sv" "$OUT/$q$m/tb_vms_hoist.sv" > "$OUT/$q$m.build.log" 2>&1 || { grep -m5 %Error "$OUT/$q$m.build.log"; fail=1; continue; }
  r=$("$OUT/$q$m/obj/Vtb_hoist" 2>/dev/null || "$OUT/$q$m/obj/Vtb_vms_hoist" 2>&1 | grep -E 'VMS_HOIST_EQUIV|MISMATCH' | tail -2); echo "$m $r"
  if [ $m = pos ]; then echo "$r" | grep -q "VMS_HOIST_EQUIV $q PASS" || fail=1; else echo "$r" | grep -Eq "VMS_HOIST_EQUIV $q FAIL checks=[0-9]+ errors=[1-9]" || fail=1; fi
  rm -rf "$OUT/$q$m/obj"
done; done
[ $fail = 0 ] && echo VMS_HOIST_EQUIV_GATE PASS || { echo VMS_HOIST_EQUIV_GATE FAIL; exit 1; }
