#!/usr/bin/env bash
set -eu
RUN=${1:?run directory}
mkdir -p "$RUN"
COMMON=(rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qfd_su_lane_relay_native.sv rtl/physical/ot_qfd_su_align_entries64.sv rtl/test/qwen_su_glue_1015/lane_relay_reference.sv rtl/test/qwen_su_glue_1015/tb_su_glue.sv)
for mc in 6 9; do
  iverilog -g2012 -s tb_su_glue -Ptb_su_glue.NATIVE_LEAF=1 -Ptb_su_glue.MC="$mc" -o "$RUN/native$mc.vvp" "${COMMON[@]}" rtl/physical/ot_qfd_su_lane_relay.sv
  vvp "$RUN/native$mc.vvp" > "$RUN/native$mc.log"
  cat "$RUN/native$mc.log"
done
python3 - "$RUN" <<'PY'
from pathlib import Path
import sys
s=Path('rtl/physical/ot_qfd_su_lane_relay.sv').read_text()
assert s.count('.W(PDW),.D(RD)')==1
Path(sys.argv[1]+'/native_mut.sv').write_text(s.replace('.W(PDW),.D(RD)','.W(PDW),.D(RD+1)'))
PY
iverilog -g2012 -s tb_su_glue -Ptb_su_glue.NATIVE_LEAF=1 -o "$RUN/mut.vvp" "${COMMON[@]}" "$RUN/native_mut.sv"
if vvp "$RUN/mut.vvp" > "$RUN/native_mut.log" 2>&1; then echo 'FAIL native relay mutant not detected';exit 1;fi
grep 'FAIL su_glue' "$RUN/native_mut.log"
echo 'PASS native relay parent reset wire, exact state/edges, actual PD mutant'
