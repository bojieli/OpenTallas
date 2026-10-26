#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}
mkdir -p "$out"
iverilog -g2012 -s tb_s81_hc_pad_roots20 -o "$out/pad.vvp" rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_pad_split.sv rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_pad_roots20.sv rtl/hdc/ot_hdc_delay.sv rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_pad_roots20.sv
vvp "$out/pad.vvp" > "$out/positive.log" 2>&1
grep -q '^PADROOTS20_PASS$' "$out/positive.log"
for mut in 1 2 3 4; do
 if vvp "$out/pad.vvp" +MUT="$mut" > "$out/mutant$mut.log" 2>&1; then
  echo "Mutant $mut unexpectedly passed";exit 1
 fi
 grep -q 'PADROOTS20_FAIL' "$out/mutant$mut.log"
done
echo PADROOTS20_COMPONENT_GATE_PASS
