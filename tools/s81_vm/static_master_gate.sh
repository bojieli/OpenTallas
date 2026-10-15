#!/bin/bash
# Full die-name VM master: 128 production SRAM models, exact scheduled endpoints,
# two base seeds, eight sticky fault witnesses, three observable numerical/phase mutants.
# Usage: static_master_gate.sh SRCDIR OUTDIR [base|capword|wfcpair|x43phase|all]
# Run heavy builds only on the admitted ot-run host; SRCDIR is a pinned flat source snapshot.
set -euo pipefail
S=${1:?source}; O=${2:?output}; TARGET=${3:-all}; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
FILES="dsfd_vm_static_fsr_bank8.sv dsfd_vm_static_fsr_quartets.sv dsfd_vm_static_read_leaf.sv dsfd_vm_static_read_quartets.sv dsfd_vm_static_read_valid.sv dsfd_vm_static_read_valid_quartets.sv dsfd_vm_static_read_router.sv dsfd_vm_static_read_quartets_p.sv dsfd_vm_static_read_valid_quartets_p.sv dsfd_vm_static_read_router_p.sv dsfd_vm_static_suhc_fsr.sv dsfd_vm_static_suhc_return_map.sv dsfd_vm_static_write_capture128.sv dsfd_vm_static_scatter_b8_out.sv dsfd_vm_static_scatter_lane.sv dsfd_vm_static_scatter.sv dsfd_vm_static_bank128.sv dsfd_vm_static_relay128.sv dsfd_vm_static_relay128_b8.sv dsfd_vm_static_relay128_b4.sv dsfd_vm_static_slice128_suhc.sv dsfd_vm_static_return.sv dsfd_vm_static_return32_native_lanes.sv dsfd_vm_static_return_bank8_profiles.sv dsfd_vm_static_return_bank8.sv dsfd_vm_static512_suhc.sv ot_sram_1r1w_512x128_m4_r2c2.v dsfd_vm_static_wdispatch128.sv dsfd_vm_static_wstage128.sv dsfd_vm_static_w0.sv dsfd_vm_static_wcontrol.sv dsfd_vm_static_wsched.sv dsfd_vm_static_rsched.sv dsfd_vm_static_landing.sv dsfd_vm_seq_static.sv dsfd_vm_seq_tile.sv dsfd_vm_static_core.sv ot_s81_vm_x34.sv ot_s81_vm_x43.sv dsfd_vm_static_capl_pipe.sv dsfd_vm_static_capl_pre.sv dsfd_vm_static_capl.sv dsfd_vm_static_cap_leaf.sv dsfd_vm_static_cap.sv dsfd_vm_static_wfc.sv dsfd_vm_static_xio.sv dsfd_sp_vm_static.sv tb_dsfd_sp_vm_static.sv"
F=(); for f in $FILES; do F+=("$S/$f"); done
run_target() {
  local name=$1 define=${2:-}
  local defs=(); [ -z "$define" ] || defs+=("+define+$define")
  [ "${VM_READ_PIPE:-0}" = 0 ] || defs+=(+define+OT_VM_NATIVE_READ)
  [ "${VM_READ_PIPE:-0}" != 2 ] || defs+=(+define+OT_VM_NATIVE_READ_PINREG)
  [ "${VM_READ_PIPE:-0}" != 4 ] || defs+=(+define+OT_VM_NATIVE_READ_L16)
  [ "${VM_CAP_PIPE:-0}" = 0 ] || defs+=(+define+OT_VM_NATIVE_CAP)
  "$V" --binary --timing -O1 -Wno-fatal -j 8 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" --top-module tb_dsfd_sp_vm_static --Mdir "$O/obj_$name" -o tb "${defs[@]}" "${F[@]}" > "$O/build_$name.log" 2>&1 || { tail -30 "$O/build_$name.log"; return 2; }
  if [ "$name" = base ]; then
    local pids=()
    for seed in 1 2; do
      "$O/obj_base/tb" +mode=0 +seed=$seed > "$O/base_s$seed.log" 2>&1 & pids+=("$!")
    done
    for pid in "${pids[@]}"; do wait "$pid" || return 2; done
    for seed in 1 2; do
      grep -q '^TB_SPVM PASS mode 0$' "$O/base_s$seed.log" || { cat "$O/base_s$seed.log"; return 1; }
    done
    pids=()
    for mode in 1 2 3 4 5 6 7 8; do
      "$O/obj_base/tb" +mode=$mode > "$O/fault_m$mode.log" 2>&1 & pids+=("$!")
    done
    for pid in "${pids[@]}"; do wait "$pid" || return 2; done
    for mode in 1 2 3 4 5 6 7 8; do
      grep -q "^TB_SPVM PASS mode $mode " "$O/fault_m$mode.log" || { cat "$O/fault_m$mode.log"; return 1; }
    done
  else
    "$O/obj_$name/tb" +mode=0 +seed=1 > "$O/$name.log" 2>&1
    grep -q '^TB_SPVM FAIL mode 0$' "$O/$name.log" || { cat "$O/$name.log"; echo "MUTANT ESCAPED $name"; return 1; }
  fi
  echo "SPVM_TARGET PASS $name"
}
case "$TARGET" in
  base) run_target base;;
  capword) run_target capword OT_VM_CAPL_MUT_WORD;;
  wfcpair) run_target wfcpair OT_VM_WFC_MUT_PAIR;;
  x43phase) run_target x43phase OT_VM_X43_MUT_PHASE;;
  all)
    run_target base
    run_target capword OT_VM_CAPL_MUT_WORD
    run_target wfcpair OT_VM_WFC_MUT_PAIR
    run_target x43phase OT_VM_X43_MUT_PHASE
    echo 'SPVM_GATE PASS';;
  *) echo "Unknown target: $TARGET" >&2; exit 2;;
esac
