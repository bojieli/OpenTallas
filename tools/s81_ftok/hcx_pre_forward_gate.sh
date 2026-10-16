#!/usr/bin/env bash
# Actual fixed pending-pre registers; component transport proof, no arithmetic or die qualification.
set -euo pipefail
out=$(realpath -m "$1")
mkdir -p "$out"
src=(rtl/dsrom_sys/s81_hcx/ot_s81_hcx_pre_forward.sv rtl/dsrom_sys/s81_hcx/test/tb_s81_hcx_pre_forward.sv)
sha256sum "${src[@]}" > "$out/sources.sha256"
iverilog -g2012 -s tb_s81_hcx_pre_forward -o "$out/nom" "${src[@]}"
vvp "$out/nom" > "$out/nom.log" 2>&1
grep -q 'HCX_PRE_FORWARD PASS checks=15 jobs=3' "$out/nom.log"
iverilog -g2012 -s tb_s81_hcx_pre_forward -Ptb_s81_hcx_pre_forward.MUT=1 -o "$out/mut" "${src[@]}"
if vvp "$out/mut" > "$out/mut.log" 2>&1; then
    echo 'FAIL current-pre mutant survived'; exit 1
fi
grep -q 'PRE_FORWARD mismatch block0' "$out/mut.log"
sha256sum --check "$out/sources.sha256" >/dev/null
echo 'HCX_PRE_FORWARD_GATE PASS nominal=15_checks mutant=current_pre_rejected cycles_added=0 vm_writes_added=0'
