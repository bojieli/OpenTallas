#!/bin/bash
# Exact gate of the static S81 VM core (dsfd_vm_static_core): Verilator build of the full real composition
# (128 SRAM macro models), base calendar (mode 0, 2 seeds) + 6 fault witnesses + 5 mutants that must FAIL the base calendar.
# Usage: tools/s81_vm/static_core_gate.sh SRCDIR OUTDIR [READS]   (SRCDIR = flat copy of the files listed below)
set -u
S=$1; O=$2; READS=${3:-4000}; mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
FILES="dsfd_vm_static_fsr_bank8.sv dsfd_vm_static_fsr_quartets.sv dsfd_vm_static_read_leaf.sv dsfd_vm_static_read_quartets.sv dsfd_vm_static_read_valid.sv dsfd_vm_static_read_valid_quartets.sv dsfd_vm_static_read_router.sv dsfd_vm_static_read_quartets_p.sv dsfd_vm_static_read_valid_quartets_p.sv dsfd_vm_static_read_router_p.sv dsfd_vm_static_suhc_fsr.sv dsfd_vm_static_suhc_return_map.sv dsfd_vm_static_write_capture128.sv dsfd_vm_static_scatter_b8_out.sv dsfd_vm_static_scatter_lane.sv dsfd_vm_static_scatter.sv dsfd_vm_static_bank128.sv
 dsfd_vm_static_relay128.sv dsfd_vm_static_relay128_b8.sv dsfd_vm_static_relay128_b4.sv dsfd_vm_static_slice128_suhc.sv dsfd_vm_static_return.sv dsfd_vm_static_return32_native_lanes.sv dsfd_vm_static_return_bank8_profiles.sv dsfd_vm_static_return_bank8.sv dsfd_vm_static512_suhc.sv
 ot_sram_1r1w_512x128_m4_r2c2.v dsfd_vm_static_wdispatch128.sv dsfd_vm_static_wstage128.sv dsfd_vm_static_w0.sv dsfd_vm_static_wcontrol.sv dsfd_vm_static_wsched.sv
 dsfd_vm_static_rsched.sv dsfd_vm_static_landing.sv dsfd_vm_seq_static.sv dsfd_vm_seq_tile.sv dsfd_vm_static_core.sv tb_dsfd_vm_static_core.sv"
F=""; for f in $FILES; do F="$F $S/$f"; done
EXTRA=""; [ "${VM_READ_PIPE:-0}" = 0 ] || EXTRA="+define+OT_VM_NATIVE_READ"; [ "${VM_READ_PIPE:-0}" = 2 ] && EXTRA="$EXTRA +define+OT_VM_NATIVE_READ_PINREG"
build(){ "$V" --binary --timing -O1 -Wno-fatal -j "${VM_BUILD_JOBS:-1}" -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" --top-module tb_dsfd_vm_static_core --Mdir "$O/obj_$1" -o tb $EXTRA ${2:-} $F > "$O/build_$1.log" 2>&1 || { echo "BUILD FAIL $1"; tail -20 "$O/build_$1.log"; }; }
build base & p0=$!
build mlane +define+OT_VM_WSCHED_MUT_LANE & p1=$!
build mdrain +define+OT_VM_WSCHED_MUT_DRAIN & p2=$!
build mslot +define+OT_VM_RSCHED_MUT_SLOT & p3=$!
build mstride +define+OT_VM_LANDING_MUT_STRIDE & p4=$!
build mmix +define+OT_VM_RSCHED_MUT_MIXSLOT & p5=$!
wait $p0 $p1 $p2 $p3 $p4 $p5
bad=0
"$O/obj_base/tb" +mode=0 +seed=1 +reads=$READS > "$O/base_s1.log" 2>&1
"$O/obj_base/tb" +mode=0 +seed=2 +reads=$READS > "$O/base_s2.log" 2>&1
for s in 1 2; do grep -q "TB_VMCORE PASS mode 0" "$O/base_s$s.log" || { echo "GATE FAIL base seed $s"; bad=1; }; done
for m in 1 2 3 4 5 6; do "$O/obj_base/tb" +mode=$m > "$O/fault_m$m.log" 2>&1; { grep -q "TB_VMCORE PASS mode $m" "$O/fault_m$m.log" && ! grep -q "TB_VMCORE FAIL mode $m" "$O/fault_m$m.log"; } || { echo "GATE FAIL fault witness $m"; bad=1; }; done
for M in mlane mdrain mslot mstride mmix; do
  "$O/obj_$M/tb" +mode=0 +seed=1 +reads=$READS > "$O/$M.log" 2>&1
  grep -q "TB_VMCORE FAIL mode 0" "$O/$M.log" || { echo "GATE FAIL mutant $M escaped"; bad=1; }
done
grep -h "RESULT\|FAULT mode" "$O"/*.log
[ $bad = 0 ] && echo "VMCORE_GATE PASS" || { echo "VMCORE_GATE FAIL"; exit 1; }
