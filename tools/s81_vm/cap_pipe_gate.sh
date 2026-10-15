#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
O=$(realpath -m "${1:?out}");mkdir -p "$O"
python3 tools/s81_vm/prepare_cap_pipe.py "$O/src"
F=("$O/src/ot_s81_vm_x34.sv" "$O/src/dsfd_vm_static_capl.sv" "$O/src/dsfd_vm_static_capl_pipe.sv" "$O/src/dsfd_vm_static_cap_leaf.sv" "$O/src/dsfd_vm_static_cap.sv" "$O/src/tb_dsfd_vm_static_cap.sv")
iverilog -g2012 -s tb_dsfd_vm_static_cap -o "$O/sim" "${F[@]}"
iverilog -g2012 -DOT_VM_CAPL_MUT_WORD -s tb_dsfd_vm_static_cap -o "$O/mut" "${F[@]}"
for s in 1 2;do vvp -n "$O/sim" +mode=0 +seed=$s > "$O/base_s$s.log";grep -q 'TB_VMCAP PASS mode 0' "$O/base_s$s.log";done
for m in 1 2 3 4 5;do vvp -n "$O/sim" +mode=$m > "$O/fault_m$m.log";grep -q "TB_VMCAP PASS mode $m" "$O/fault_m$m.log";done
vvp -n "$O/mut" +mode=0 > "$O/mut_word.log"
grep -q 'TB_VMCAP FAIL mode 0' "$O/mut_word.log"
grep -h TB_VMCAP "$O"/*.log
echo CAP_PIPE_PRODUCTION_GATE_PASS
