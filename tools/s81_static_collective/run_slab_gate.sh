#!/usr/bin/env bash
# Full static collective slab component gate (tb_s81_static_collective_slab: actual slab RTL incl. the
# s81_static_vm_boundary leaf + one real dsfd_sp_vm with its 128 SRAM macros). Reproduces the 10-15
# results/rtl/s81_static_vm_boundary_extract_1015 base/mutant runs from the current source.
#   run_slab_gate.sh WORK [MUT [PINCAP]]   MUT=1: vm_boundary flips t_vm bit 31 on HC writes (must FAIL); MUT=2: the static host
#   queue drops the completion pulse (the slot beat carries none: must FAIL); MUT=3: calendar controller reads the next ROM row (must FAIL)
#   PINCAP (default 1) = native VM boundary write-path pin capture (+1 edge on t_vm)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd); W=$(mkdir -p "$1" && cd "$1" && pwd); MUT=${2:-0}; PINCAP=${3:-1}; DEFS=(); [ "$MUT" = 3 ] && { DEFS=(+define+OT_S81_COLL_CAL_MUT_ROW); MUT=0; MUTANT=1; }
V=${OT_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
cd "$W"; python3 "$ROOT/tools/s81_static_collective/build_slab_fixture.py" --out "$W" > fixture.json
S=$ROOT/rtl/dsrom_sys
SRC=("$ROOT/rtl/ot_fp32_rne_pkg.sv" "$ROOT/rtl/hdc/ot_hdc_prefix.sv" "$ROOT/rtl/link/ot_link_crc32.sv"
 "$S"/s81_static_collective/{dsfd_sp_collective_static_c,s81_static_collective_slab,s81_static_calendar_controller,s81_static_fmt1_rank_dynamic_clocked,s81_static_fmt1_rank_dynamic,s81_static_fmt1_core_dynamic,s81_static_fmt1_lane_dynamic,s81_static_fmt1_codec_dynamic,s81_static_tp4_endpoint_dynamic,s81_static_fmt1_gearbox,s81_static_fmt1_channels_clocked,s81_static_raw_fmt1_lane,s81_static_raw_fmt1_codec,s81_static_raw_vm_rows,s81_static_vm_boundary,s81_static_host_queue}.sv
 "$S"/s81_static_hc/{s81_static_hc_reduce,s81_static_hc_assemble}.sv
 "$S"/s81_ph/{ot_s81ph_fp32_add_rne_preexp,ot_s81ph_coll_rstc,ot_s81_pll_bb}.sv
 "$S"/s81_ph/coll/{dsfd_coll_static_channels,dsfd_coll_ck,ot_s81ph_ckbuf}.sv
 "$ROOT/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v"
 "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
 "$ROOT/tools/s81_static_collective/tb_s81_static_collective_slab.sv")
# the VM's file closure from its current source (its module set evolves with the VM owners' successors; a hardcoded
# list went stale: dsfd_vm_seq_tile / dsfd_vm_static_return32_native_lanes)
mapfile -t VMF < <(cd "$ROOT" && python3 tools/die_port_bind.py none --closure dsfd_sp_vm)
[ ${#VMF[@]} -gt 10 ] || { echo "SLAB_GATE VM closure failed"; exit 2; }
SRC=("${SRC[@]:0:${#SRC[@]}-1}" "${VMF[@]}" "${SRC[@]: -1}")
mapfile -t SRC < <(for f in "${SRC[@]}"; do realpath "$f"; done | awk '!seen[$0]++')
for f in "${SRC[@]}"; do [ -f "$f" ] || { echo "SLAB_GATE missing $f"; exit 2; }; done
sha256sum "${SRC[@]}" > sources.sha256
"$V" --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81_static_collective_slab -GMUT="$MUT" -GVMB_PINCAP="$PINCAP" "${DEFS[@]}" --Mdir obj "${SRC[@]}" > build.log 2>&1
set +e; ./obj/Vtb_s81_static_collective_slab > run.log 2>&1; rc=$?; set -e
# Preserve the actual work-count line for closure-loop non-vacuity admission.
# Verilator appends four report lines after the DUT summary.
grep -E '^PASS fullstatic slab|^FAIL|Assertion failed' run.log || true
tail -n 3 run.log
if [ "$MUT" != 0 ] || [ -n "${MUTANT:-}" ]; then
  if [ $rc -ne 0 ] || grep -q 'Assertion failed' run.log; then echo "SLAB_GATE MUTANT FAIL (detected)"; exit 1; fi
  echo "SLAB_GATE MUTANT UNDETECTED"; exit 0
fi
[ $rc -eq 0 ] && grep -q '^PASS fullstatic slab' run.log && { echo "SLAB_GATE PASS"; exit 0; }
echo "SLAB_GATE FAIL rc=$rc"; exit 1
