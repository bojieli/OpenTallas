#!/bin/bash
# claude S81 VM F2 2026-10-15: cap lane PIPE=2 (pin-stage decode) == PIPE=1 cycle-exact; mutant must FAIL.
set -euo pipefail
cd "$(dirname "$0")/../.."
O=$(realpath -m "${1:?outdir}"); variant=${2:?base or mutant}; mkdir -p "$O"; R=rtl/dsrom_sys/s81_ph
defs=(); [ "$variant" = base ] || defs+=(-DOT_VM_CAP_PRE_MUT_TGT)
iverilog -g2012 "${defs[@]}" -s tb_dsfd_vm_static_cap_leaf_pre_equiv -o "$O/sim_$variant" \
  "$R/vm/dsfd_vm_static_capl.sv" "$R/vm/dsfd_vm_static_capl_pipe.sv" "$R/vm/dsfd_vm_static_capl_pre.sv" \
  "$R/vm/dsfd_vm_static_cap_leaf.sv" "$R/test/tb_dsfd_vm_static_cap_leaf_pre_equiv.sv"
rc=0
for seed in 42 137; do
  vvp -n "$O/sim_$variant" +seed=$seed > "$O/${variant}_$seed.log" || rc=1
  cat "$O/${variant}_$seed.log"
  grep -q '^PASS cap_leaf_pre_equivalence cycles=12000' "$O/${variant}_$seed.log" || rc=1
done
[ $rc = 0 ] && echo "CAP_LEAF_PRE_EQUIV_GATE PASS $variant" || echo "CAP_LEAF_PRE_EQUIV_GATE FAIL $variant"
exit $rc
