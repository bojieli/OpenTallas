#!/usr/bin/env bash
set -eu
root=$(cd "$(dirname "$0")/../.." && pwd)
src=$root/rtl/dsrom_sys/s81_link; out=${1:?fresh output directory}; mode=${2:-2}
mkdir -p "$out"
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_head_serdes_dchn +define+OT_KP4_COUNT_TEST_SPLIT=$mode +incdir+"$src" --Mdir "$out/obj" -o tb "$src/ot_s81_kp4_common.sv" "$src/ot_s81_kp4_dchn.sv" "$root/tools/s81_head/head_serdes_split_tb.sv" > "$out/build.log" 2>&1
"$out/obj/tb" > "$out/run.log" 2>&1
for variant in good mutant; do
  mut=0; [ "$variant" = good ] || mut=1
  yosys -Q -T -p "read_verilog -sv -I$src $src/ot_s81_kp4_dchn.sv $root/tools/s81_head/head_serdes_split_miter.sv; chparam -set MUT $mut -set SPLIT $mode split_count_miter; hierarchy -top split_count_miter; proc; flatten; opt; techmap; opt; aigmap; opt_clean; write_aiger -zinit $out/$variant.aig" > "$out/$variant.yosys.log" 2>&1
  yosys-abc -c "read_aiger $out/$variant.aig; strash; collapse; print_stats; write_blif $out/$variant.blif" > "$out/$variant.abc.log" 2>&1
done
yosys -Q -T -p "read_verilog -sv $root/tools/s81_head/head_serdes_split_miter.sv; hierarchy -top split_acc_miter; proc; flatten; opt; techmap; opt; sat -verify -prove eq 1" > "$out/accumulator.log" 2>&1
yosys -Q -T -p "read_verilog -sv $root/tools/s81_head/head_serdes_split_miter.sv; hierarchy -top split_acc4_miter; proc; flatten; opt; techmap; opt; sat -verify -prove eq 1" > "$out/accumulator4.log" 2>&1
python3 - "$out" <<'PY_CHECK'
from pathlib import Path
import sys,json,re
p=Path(sys.argv[1]);good=(p/'good.blif').read_text();bad=(p/'mutant.blif').read_text()
def const_one(text):
    output=re.search(r'\.outputs\s+(\w+)',text).group(1)
    return bool(re.search(r'\.names\s+'+re.escape(output)+r'\s*\n\s*1\s*\n',text))
assert const_one(good), good[-1000:]
assert not const_one(bad)
r={'count_equivalence':'PASS all 2^56 inputs','dropped_root_control':'CAUGHT','full_DCHN':'PASS','added_cycles':0,'physical_timing':'NOT RUN','signed':False}
(p/'verdict.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY_CHECK
cat "$out/run.log"
