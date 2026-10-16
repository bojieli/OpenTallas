#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory};mkdir -p "$out"
iverilog -g2012 -s tb_s81_hc_crooty_roots -o "$out/root.vvp" \
 rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crooty.sv \
 rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_croot_roots.sv \
 rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_crooty_roots.sv
vvp "$out/root.vvp" > "$out/positive.log" 2>&1
grep -q '^CROOTY_ROOTS_PASS$' "$out/positive.log"
for mut in $(seq 1 12);do
 if vvp "$out/root.vvp" +STOP="$mut" > "$out/stopped_root$mut.log" 2>&1;then exit 1;fi
 grep -q 'CROOTY_ROOTS_FAIL' "$out/stopped_root$mut.log"
done
echo CROOTY_ROOTS_COMPONENT_GATE_PASS
