#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?outdir}; mode=${2:-base}; mkdir -p "$out"; defs=()
case "$mode" in base);; drop) defs+=(-DOT_VM_LANDING_JOIN_MUT_DROP);; *) exit 2;; esac
iverilog -g2012 "${defs[@]}" -s tb -o "$out/tb" tools/s81_vm/landing_fault_join_bench.sv rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_landing_fault_join.sv
vvp "$out/tb" | tee "$out/run.log"
