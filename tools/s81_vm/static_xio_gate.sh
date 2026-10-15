#!/bin/bash
set -eu
cd "$(dirname "$0")/../.."
O=${1:?output directory}; mkdir -p "$O"
R=rtl/dsrom_sys/s81_ph
for variant in base mutant; do
    flags=()
    if [[ $variant == mutant ]]; then flags=(-DOT_VM_XIO_MUT_TAG); fi
    iverilog -g2012 "${flags[@]}" -s tb_dsfd_vm_static_xio -o "$O/$variant" "$R/vm/ot_s81_vm_x43.sv" "$R/vm/dsfd_vm_static_xio.sv" "$R/test/tb_dsfd_vm_static_xio.sv"
done
vvp -n "$O/base" > "$O/base.log"
grep -q 'TB_XIO PASS' "$O/base.log"
if vvp -n "$O/mutant" > "$O/mutant.log"; then
    echo 'XIO_GATE FAIL tag mutant escaped'; exit 1
fi
grep -q 'tuple' "$O/mutant.log"
cat "$O/base.log"
echo 'XIO_GATE PASS tag mutant rejected'
