#!/bin/bash
set -eu
S=$1
O=$2
mkdir -p "$O"
common=("$S/dsfd_vm_static_cap.sv" "$S/dsfd_vm_static_cap_leaf.sv" "$S/dsfd_vm_static_capl.sv" "$S/dsfd_vm_static_xio.sv" "$S/ot_s81_vm_x34.sv" "$S/ot_s81_vm_x43.sv")
iverilog -g2012 -s tb_edge_clock_categories -o "$O/bind.vvp" "$S/tb_edge_clock_categories.sv" "${common[@]}" "$S/dsfd_vm_static_wfc.sv" > "$O/build_bind.log" 2>&1
vvp "$O/bind.vvp" > "$O/run_bind.log" 2>&1
grep -qx EDGE_BIND_PASS "$O/run_bind.log"
iverilog -g2012 -s tb_edge_clock_categories -o "$O/bind_mut.vvp" "$S/tb_edge_clock_categories.sv" "${common[@]}" "$S/dsfd_vm_static_wfc_mut.sv" > "$O/build_bind_mut.log" 2>&1
vvp "$O/bind_mut.vvp" > "$O/run_bind_mut.log" 2>&1
grep -qx EDGE_BIND_FAIL "$O/run_bind_mut.log"
iverilog -g2012 -s tb_dsfd_vm_static_xio -o "$O/xio.vvp" "$S/tb_dsfd_vm_static_xio.sv" "${common[@]}" > "$O/build_xio.log" 2>&1
vvp "$O/xio.vvp" > "$O/run_xio.log" 2>&1
grep -q 'TB_XIO PASS' "$O/run_xio.log"
iverilog -g2012 -s tb_dsfd_vm_static_cap -o "$O/cap.vvp" "$S/tb_dsfd_vm_static_cap.sv" "${common[@]}" > "$O/build_cap.log" 2>&1
vvp "$O/cap.vvp" > "$O/run_cap.log" 2>&1
grep -qx 'TB_VMCAP PASS mode 0' "$O/run_cap.log"
sha256sum "$S"/*.sv "$S/source_receipt.json" > "$O/input_sha256.txt"
for n in bind bind_mut xio cap;do tail -2 "$O/run_$n.log";done
echo EDGE_CATEGORY_GATE_PASS
