#!/usr/bin/env bash
# Full static collective slab component gate (tb_s81_static_collective_slab: actual slab RTL incl. the
# s81_static_vm_boundary leaf + one real dsfd_sp_vm with its 128 SRAM macros). Reproduces the 10-15
# results/rtl/s81_static_vm_boundary_extract_1015 base/mutant runs from the current source.
#   run_slab_gate.sh WORK [MUT]    MUT=1: vm_boundary flips t_vm bit 31 on HC writes (must FAIL); MUT=2: the static host
#   queue never pops (the host completion is never sent: must FAIL)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd); W=$(mkdir -p "$1" && cd "$1" && pwd); MUT=${2:-0}
V=${OT_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
cd "$W"; python3 "$ROOT/tools/s81_static_collective/build_slab_fixture.py" --out "$W" > fixture.json
S=$ROOT/rtl/dsrom_sys
SRC=("$ROOT/rtl/ot_fp32_rne_pkg.sv" "$ROOT/rtl/hdc/ot_hdc_prefix.sv" "$ROOT/rtl/link/ot_link_crc32.sv"
 "$S"/s81_static_collective/{dsfd_sp_collective_static_c,s81_static_collective_slab,s81_static_calendar_controller,s81_static_fmt1_rank_dynamic_clocked,s81_static_fmt1_rank_dynamic,s81_static_fmt1_core_dynamic,s81_static_fmt1_lane_dynamic,s81_static_fmt1_codec_dynamic,s81_static_tp4_endpoint_dynamic,s81_static_fmt1_gearbox,s81_static_fmt1_channels_clocked,s81_static_raw_fmt1_lane,s81_static_raw_fmt1_codec,s81_static_raw_vm_rows,s81_static_vm_boundary,s81_static_host_queue}.sv
 "$S"/s81_static_hc/{s81_static_hc_reduce,s81_static_hc_assemble}.sv
 "$S"/s81_ph/{ot_s81ph_fp32_add_rne_preexp,ot_s81ph_coll_rstc,ot_s81_pll_bb}.sv
 "$S"/s81_ph/coll/{dsfd_coll_static_channels,dsfd_coll_ck,ot_s81ph_ckbuf}.sv
 "$S"/s81_ph/vm/{dsfd_sp_vm_static,dsfd_vm_static_core,dsfd_vm_static512_suhc,dsfd_vm_static_slice128_suhc,dsfd_vm_static_bank128,dsfd_vm_static_relay128,dsfd_vm_static_scatter,dsfd_vm_static_return,dsfd_vm_static_suhc_fsr,dsfd_vm_static_suhc_return_map,dsfd_vm_static_wdispatch128,dsfd_vm_static_wstage128,dsfd_vm_static_wsched,dsfd_vm_static_rsched,dsfd_vm_static_landing,dsfd_vm_static_wfc,dsfd_vm_static_cap,dsfd_vm_static_capl,dsfd_vm_static_xio,dsfd_vm_seq_static,ot_s81_vm_x34,ot_s81_vm_x43,dsfd_vm_static_fsr_quartets,dsfd_vm_static_write_capture128,dsfd_vm_static_scatter_b8_out,dsfd_vm_static_relay128_b8,dsfd_vm_static_relay128_b4,dsfd_vm_static_w0,dsfd_vm_static_wcontrol,dsfd_vm_static_cap_leaf,dsfd_vm_static_fsr_bank8}.sv
 "$ROOT/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v"
 "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
 "$ROOT/tools/s81_static_collective/tb_s81_static_collective_slab.sv")
for f in "${SRC[@]}"; do [ -f "$f" ] || { echo "SLAB_GATE missing $f"; exit 2; }; done
sha256sum "${SRC[@]}" > sources.sha256
"$V" --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81_static_collective_slab -GMUT="$MUT" --Mdir obj "${SRC[@]}" > build.log 2>&1
set +e; ./obj/Vtb_s81_static_collective_slab > run.log 2>&1; rc=$?; set -e
tail -n 3 run.log
if [ "$MUT" != 0 ]; then
  if [ $rc -ne 0 ] || grep -q 'Assertion failed' run.log; then echo "SLAB_GATE MUTANT FAIL (detected)"; exit 1; fi
  echo "SLAB_GATE MUTANT UNDETECTED"; exit 0
fi
[ $rc -eq 0 ] && grep -q '^PASS fullstatic slab' run.log && { echo "SLAB_GATE PASS"; exit 0; }
echo "SLAB_GATE FAIL rc=$rc"; exit 1
