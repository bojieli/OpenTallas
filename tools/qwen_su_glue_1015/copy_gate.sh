#!/usr/bin/env bash
set -eu
RUN=${1:?run directory}
mkdir -p "$RUN"
COMMON=(tools/qwen_su_glue_1015/base_inventory/qfd_su_static_copy.sv tools/qwen_su_glue_1015/base_inventory/qfd_su_vm_pack.sv rtl/physical/qfd_su_static_copy_entries.sv)
for bench in tb_qfd_su_copy_entries tb_copy_reset; do
  iverilog -g2012 -s "$bench" -o "$RUN/$bench.vvp" "${COMMON[@]}" rtl/physical/ot_qfd_su_copy_core.sv "rtl/test/qwen_su_glue_1015/$bench.sv"
  vvp "$RUN/$bench.vvp" > "$RUN/$bench.log"
  cat "$RUN/$bench.log"
done
for mutant in data latency; do
  param=DATA_MUT
  if [ "$mutant" = latency ]; then param=LATENCY_MUT; fi
  iverilog -g2012 -s tb_qfd_su_copy_entries -Ptb_qfd_su_copy_entries."$param"=1 -o "$RUN/$mutant.vvp" "${COMMON[@]}" rtl/physical/ot_qfd_su_copy_core.sv rtl/test/qwen_su_glue_1015/tb_qfd_su_copy_entries.sv
  if vvp "$RUN/$mutant.vvp" > "$RUN/$mutant.log" 2>&1; then echo "FAIL copy mutant $mutant not detected";exit 1;fi
  grep 'FAIL' "$RUN/$mutant.log"
done
python3 - "$RUN" <<'PY'
from pathlib import Path
import sys
s=Path('rtl/physical/ot_qfd_su_copy_core.sv').read_text()
assert s.count('always @(posedge ck or negedge rst_n)')==1
Path(sys.argv[1]+'/clock_mut.sv').write_text(s.replace('always @(posedge ck or negedge rst_n)','always @(negedge ck or negedge rst_n)'))
PY
iverilog -g2012 -s tb_copy_reset -o "$RUN/clock.vvp" "${COMMON[@]}" "$RUN/clock_mut.sv" rtl/test/qwen_su_glue_1015/tb_copy_reset.sv
if vvp "$RUN/clock.vvp" > "$RUN/clock.log" 2>&1; then echo 'FAIL copy clock mutant not detected'; exit 1;fi
grep 'FAIL' "$RUN/clock.log"
echo 'PASS copy actual-source cut, raw12288words and reset/fault equivalence, three mutants'
