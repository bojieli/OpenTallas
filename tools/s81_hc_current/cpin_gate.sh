#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}
mkdir -p "$out"
cp=rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_cpin_calendar.sv
tb=rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_cpin_calendar.sv
iverilog -g2012 -s tb_s81_hc_cpin_calendar -o "$out/cpin.vvp" "$cp" "$tb"
vvp "$out/cpin.vvp" > "$out/positive.log" 2>&1
grep -q '^CPIN_CALENDAR_PASS$' "$out/positive.log"
if vvp "$out/cpin.vvp" +STOP=1 > "$out/stopped_root.log" 2>&1; then exit 1; fi
grep -q 'CPIN_CALENDAR_FAIL' "$out/stopped_root.log"
sed 's/n_y_tag <= y_tag;/n_y_tag <= y_tag ^ 1;/' "$cp" > "$out/tag_mutant.sv"
iverilog -g2012 -s tb_s81_hc_cpin_calendar -o "$out/tag.vvp" "$out/tag_mutant.sv" "$tb"
if vvp "$out/tag.vvp" > "$out/tag_mutant.log" 2>&1; then exit 1; fi
grep -q 'CPIN_CALENDAR_FAIL' "$out/tag_mutant.log"
echo CPIN_CALENDAR_COMPONENT_GATE_PASS
