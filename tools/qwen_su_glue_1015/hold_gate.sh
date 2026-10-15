#!/usr/bin/env bash
set -eu
RUN=${1:?run directory}
mkdir -p "$RUN"
python3 - "$RUN" <<'PY'
from pathlib import Path
import sys
s=Path('rtl/physical/ot_qfd_su_align_group4_hold.sv').read_text().replace('module ot_qfd_su_align_group4_hold','module ot_qfd_su_align_group4',1)
r=Path(sys.argv[1]);(r/'align_hold_alias.sv').write_text(s)
(r/'align_hold_mutant.sv').write_text(s.replace('.W(12),.D(ML),.RESET(1)','.W(12),.D(ML-1),.RESET(1)'))
PY
COMMON=(rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qfd_su_lane_relay.sv rtl/physical/ot_qfd_su_delay_hold.sv rtl/test/qwen_su_glue_1015/lane_relay_reference.sv rtl/test/qwen_su_glue_1015/tb_su_glue.sv)
for mc in 6 9; do
  iverilog -g2012 -s tb_su_glue -Ptb_su_glue.MC="$mc" -o "$RUN/hold$mc.vvp" "${COMMON[@]}" "$RUN/align_hold_alias.sv"
  vvp "$RUN/hold$mc.vvp" > "$RUN/hold$mc.log"
  cat "$RUN/hold$mc.log"
done
iverilog -g2012 -s tb_su_glue -o "$RUN/mut.vvp" "${COMMON[@]}" "$RUN/align_hold_mutant.sv"
if vvp "$RUN/mut.vvp" > "$RUN/hold_mut.log" 2>&1; then echo 'FAIL hold mask mutant not detected';exit 1;fi
grep 'FAIL su_glue' "$RUN/hold_mut.log"
echo 'PASS actual hold-source shift state/edges and actual mask mutant'
