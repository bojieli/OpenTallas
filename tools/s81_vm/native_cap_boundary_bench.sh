#!/bin/bash
# Source-bound composition witness for actual E8 capture leaves. The word mutant
# is a real RTL change and this command fails the same numerical/cycle oracle.
set -euo pipefail
cd "$(dirname "$0")/../.."
O=${1:?output}; variant=${2:?base or word}; mkdir -p "$O"
R=rtl/dsrom_sys/s81_ph
args=()
case "$variant" in base) ;; word) args+=(-DOT_VM_CAPL_MUT_WORD);; *) exit 2;; esac
iverilog -g2012 "${args[@]}" -o "$O/sim" -s tb_dsfd_vm_static_cap \
 "$R/vm/ot_s81_vm_x34.sv" "$R/vm/dsfd_vm_static_capl_pipe.sv dsfd_vm_static_capl.sv" "$R/vm/dsfd_vm_static_cap_leaf.sv" \
 "$R/vm/dsfd_vm_static_cap.sv" "$R/test/tb_dsfd_vm_static_cap.sv"
vvp -n "$O/sim" +mode=0 +seed=1 > "$O/run.log"
cat "$O/run.log"
grep -q '^TB_VMCAP PASS mode 0$' "$O/run.log"
