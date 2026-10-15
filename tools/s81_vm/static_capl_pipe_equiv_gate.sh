#!/bin/bash
# Exact retiming proof: registered-merge output is legacy+1 serial edge, II1;
# compare every emitted valid word/header and sticky fault, including tie-full,
# immediate entry reuse, partial flushes and repeated mid-flight reset.
set -euo pipefail
cd "$(dirname "$0")/../.."
O=${1:?outdir}; mkdir -p "$O"; R=rtl/dsrom_sys/s81_ph
for variant in base word; do
  defs=(); [ "$variant" = base ] || defs+=(-DOT_VM_CAPL_MUT_WORD)
  iverilog -g2012 "${defs[@]}" -s tb_dsfd_vm_static_capl_pipe_equiv -o "$O/sim_$variant" \
    "$R/vm/dsfd_vm_static_capl.sv" "$R/vm/dsfd_vm_static_capl_pipe.sv" "$R/test/tb_dsfd_vm_static_capl_pipe_equiv.sv"
  for seed in 42 137; do
    vvp -n "$O/sim_$variant" +seed=$seed > "$O/${variant}_$seed.log"
    grep -q '^PASS staged_equivalence cycles=6000' "$O/${variant}_$seed.log"
  done
done
echo CAPL_PIPE_EQUIV_GATE_PASS
