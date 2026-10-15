#!/bin/bash
# Exact gate of the static capture face dsfd_vm_static_cap (16 static lanes + 16 fixed-phase 3:4 transfers, production
# shape 128 roots): base run (every row word-exact on its one fixed stream edge, partial rows at the drained flush),
# five fault witnesses (alias, alignment, range, duplicate word, capture status) and one mutant (row1 words written
# into the row0 slot: must FAIL).  Usage: tools/s81_vm/static_cap_gate.sh OUTDIR
set -u
cd "$(dirname "$0")/../.."
O=${1:?outdir}; mkdir -p "$O"; R=rtl/dsrom_sys/s81_ph; bad=0
F="$R/vm/ot_s81_vm_x34.sv $R/vm/dsfd_vm_static_capl.sv $R/vm/dsfd_vm_static_cap_leaf.sv $R/vm/dsfd_vm_static_cap.sv $R/test/tb_dsfd_vm_static_cap.sv"
iverilog -g2012 -o "$O/sim" -s tb_dsfd_vm_static_cap $F || exit 2
iverilog -g2012 -DOT_VM_CAPL_MUT_WORD -o "$O/mut" -s tb_dsfd_vm_static_cap $F || exit 2
for s in 1 2; do vvp -n "$O/sim" +mode=0 +seed=$s > "$O/base_s$s.log"; grep -q "TB_VMCAP PASS mode 0" "$O/base_s$s.log" || { echo "GATE FAIL base seed $s"; bad=1; }; done
for m in 1 2 3 4 5; do vvp -n "$O/sim" +mode=$m > "$O/fault_m$m.log"; grep -q "TB_VMCAP PASS mode $m" "$O/fault_m$m.log" || { echo "GATE FAIL witness $m"; bad=1; }; done
vvp -n "$O/mut" +mode=0 > "$O/mut_word.log"; grep -q "TB_VMCAP FAIL mode 0" "$O/mut_word.log" || { echo "GATE FAIL mutant escaped"; bad=1; }
grep -h "TB_VMCAP" "$O"/*.log
[ $bad = 0 ] && echo "VMCAP_GATE PASS" || { echo "VMCAP_GATE FAIL"; exit 1; }
