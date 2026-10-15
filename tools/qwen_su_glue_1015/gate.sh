#!/usr/bin/env bash
set -eu
RUN=${1:?run directory required}
mkdir -p "$RUN"
COMMON=(rtl/hdc/ot_hdc_delay.sv rtl/test/qwen_su_glue_1015/lane_relay_reference.sv rtl/test/qwen_su_glue_1015/tb_su_glue.sv)
for mc in 6 9; do
  iverilog -g2012 -s tb_su_glue -Ptb_su_glue.MC="$mc" -o "$RUN/gate_mc$mc.vvp" "${COMMON[@]}" rtl/physical/ot_qfd_su_lane_relay.sv rtl/physical/ot_qfd_su_align_entries64.sv
  vvp "$RUN/gate_mc$mc.vvp" > "$RUN/gate_mc$mc.log"
  cat "$RUN/gate_mc$mc.log"
done
python3 - "$RUN" <<'PY'
import sys
from pathlib import Path
r=Path(sys.argv[1])
s=Path('rtl/physical/ot_qfd_su_lane_relay.sv').read_text()
assert s.count('.W(PDW),.D(RD)')==1
(r/'relay_mutant.sv').write_text(s.replace('.W(PDW),.D(RD)', '.W(PDW),.D(RD+1)'))
s=Path('rtl/physical/ot_qfd_su_align_entries64.sv').read_text()
assert s.count('.W(12),.D(ML),.RESET(1)')==1
(r/'align_mutant.sv').write_text(s.replace('.W(12),.D(ML),.RESET(1)','.W(12),.D(ML-1),.RESET(1)'))
PY
for mutant in relay align; do
  relay=rtl/physical/ot_qfd_su_lane_relay.sv
  align=rtl/physical/ot_qfd_su_align_entries64.sv
  if [ "$mutant" = relay ]; then relay="$RUN/relay_mutant.sv"; else align="$RUN/align_mutant.sv"; fi
  iverilog -g2012 -s tb_su_glue -o "$RUN/${mutant}_mut.vvp" "${COMMON[@]}" "$relay" "$align"
  if vvp "$RUN/${mutant}_mut.vvp" > "$RUN/${mutant}_mut.log" 2>&1; then echo "FAIL undetected $mutant mutant"; exit 1; fi
  grep 'FAIL su_glue' "$RUN/${mutant}_mut.log"
done
echo 'PASS su_glue gate two configurations and two actual-source mutants'
