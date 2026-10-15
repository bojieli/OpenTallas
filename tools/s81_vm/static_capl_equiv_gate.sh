#!/bin/bash
# Compare the structural rewrite against the immutable pre-rewrite component,
# including all next-state words, faults and output/flush cycles.
set -euo pipefail
cd "$(dirname "$0")/../.."
O=${1:?outdir}; mkdir -p "$O"
P=rtl/dsrom_sys/s81_ph
BASE=dfe28f6f8
# This exact historical source is the reference, never the rewritten worktree.
git show "$BASE:$P/vm/dsfd_vm_static_capl.sv" | sed 's/module dsfd_vm_static_capl #/module dsfd_vm_static_capl_old #/' > "$O/old.sv"
for mutation in base word; do
  defs=(); [ "$mutation" = base ] || defs+=(-DOT_VM_CAPL_MUT_WORD)
  iverilog -g2012 "${defs[@]}" -s tb_dsfd_vm_static_capl_equiv -o "$O/sim_$mutation" "$O/old.sv" "$P/vm/dsfd_vm_static_capl.sv" "$P/test/tb_dsfd_vm_static_capl_equiv.sv"
  for seed in 42 137; do
    vvp -n "$O/sim_$mutation" +seed=$seed > "$O/${mutation}_$seed.log"
    grep -q '^PASS equivalence cycles=6000' "$O/${mutation}_$seed.log"
  done
done
echo CAPL_EQUIV_GATE_PASS
