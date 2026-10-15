#!/usr/bin/env bash
set -eu
RUN=${1:?run directory}
mkdir -p "$RUN"
python3 - "$RUN" <<'PY'
from pathlib import Path
import re,sys
r=Path(sys.argv[1]);s=Path('rtl/physical/ot_qfd_su_copy_core_bnd8.sv').read_text();core=s.replace('module ot_qfd_su_copy_core_bnd8','module ot_qfd_su_copy_core',1)
(r/'core_alias.sv').write_text(core)
assert core.count('always @(posedge ck or negedge rst_n)')==1
(r/'clock_mut.sv').write_text(core.replace('always @(posedge ck or negedge rst_n)','always @(negedge ck or negedge rst_n)'))
fn=re.search(r' function automatic bounds_bad.*? endfunction',s,re.S).group()
orig=Path('rtl/physical/ot_qfd_su_copy_core.sv').read_text();ref=re.search(r"\{1'b0,cp\[24:1\]\}\+\(\{18'd0,beats\}<<6\)>25'h1000000",orig).group().replace('cp[24:1]','base').replace('beats','count')
formal='module copy_bounds_formal(input[23:0]base,input[6:0]count,output equal);\n'+fn+'\nwire old_bad='+ref+';\nassign equal=(old_bad==bounds_bad(base,count));\nendmodule\n'
(r/'formal_actual.sv').write_text(formal)
assert formal.count('(&base[23:13])')==1
(r/'formal_mut.sv').write_text(formal.replace('(&base[23:13])','(|base[23:13])'))
PY
yosys -p "read_verilog -sv $RUN/formal_actual.sv; prep -top copy_bounds_formal; sat -verify -prove equal 1 -show-inputs" > "$RUN/formal_actual.log" 2>&1
grep 'SAT proof finished' "$RUN/formal_actual.log"
if yosys -p "read_verilog -sv $RUN/formal_mut.sv; prep -top copy_bounds_formal; sat -verify -prove equal 1 -show-inputs" > "$RUN/formal_mut.log" 2>&1; then echo 'FAIL bad bounds source mutant unrecognized';exit 1;fi
grep 'ERROR: Called with -verify and proof did fail' "$RUN/formal_mut.log"
COMMON=(tools/qwen_su_glue_1015/base_inventory/qfd_su_static_copy.sv tools/qwen_su_glue_1015/base_inventory/qfd_su_vm_pack.sv rtl/physical/qfd_su_static_copy_entries.sv)
for bench in tb_qfd_su_copy_entries tb_copy_reset; do
  iverilog -g2012 -s "$bench" -o "$RUN/$bench.vvp" "${COMMON[@]}" "$RUN/core_alias.sv" "rtl/test/qwen_su_glue_1015/$bench.sv"
  vvp "$RUN/$bench.vvp" > "$RUN/$bench.log"
  cat "$RUN/$bench.log"
done
for mutant in data latency; do
  param=DATA_MUT; if [ "$mutant" = latency ]; then param=LATENCY_MUT; fi
  iverilog -g2012 -s tb_qfd_su_copy_entries -Ptb_qfd_su_copy_entries."$param"=1 -o "$RUN/$mutant.vvp" "${COMMON[@]}" "$RUN/core_alias.sv" rtl/test/qwen_su_glue_1015/tb_qfd_su_copy_entries.sv
  if vvp "$RUN/$mutant.vvp" > "$RUN/$mutant.log" 2>&1; then echo "FAIL copy mutant $mutant unrecognized";exit 1;fi
  grep 'FAIL' "$RUN/$mutant.log"
done
iverilog -g2012 -s tb_copy_reset -o "$RUN/clock.vvp" "${COMMON[@]}" "$RUN/clock_mut.sv" rtl/test/qwen_su_glue_1015/tb_copy_reset.sv
if vvp "$RUN/clock.vvp" > "$RUN/clock.log" 2>&1; then echo 'FAIL bad clock mutant unrecognized';exit 1;fi
grep 'FAIL' "$RUN/clock.log"
echo 'PASS actual-source bounds SAT,12288rawwords,reset/fault equivalence,four mutants'
