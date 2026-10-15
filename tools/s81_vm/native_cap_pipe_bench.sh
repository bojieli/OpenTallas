#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
O=$(realpath -m "${1:?out}");variant=${2:?base or word};PIPE=${3:-1};mkdir -p "$O"
python3 tools/s81_vm/prepare_cap_pipe.py "$O/src" "$PIPE"
defs=();case "$variant" in base);;word)defs+=(-DOT_VM_CAPL_MUT_WORD);;flush)defs+=(-DOT_VM_CAP_CTL_MUT_FLUSH);;x34)defs+=(-DOT_VM_X34_MUT_PHASE);;x34s)defs+=(-DOT_VM_X34_MUT_SBANK);;*)exit 2;;esac
iverilog -g2012 "${defs[@]}" -s tb_dsfd_vm_static_cap -o "$O/sim" "$O/src/ot_s81_vm_x34.sv" "$O/src/dsfd_vm_static_capl.sv" "$O/src/dsfd_vm_static_capl_pipe.sv" "$O/src/dsfd_vm_static_capl_pre.sv" "$O/src/dsfd_vm_static_cap_leaf.sv" "$O/src/dsfd_vm_static_cap.sv" "$O/src/tb_dsfd_vm_static_cap.sv"
vvp -n "$O/sim" +mode=0 +seed=1 > "$O/run.log"
cat "$O/run.log"
grep -q '^TB_VMCAP PASS mode 0$' "$O/run.log"
