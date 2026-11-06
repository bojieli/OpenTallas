#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /work
LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
for top in baseline candidate; do
 python3 - "$top" <<'PY'
import sys,glob
from pathlib import Path
top=sys.argv[1];libs=sorted(glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*'));libs=[p for p in libs if 'FAKE' not in p]
libargs=' '.join('-liberty '+p for p in libs)
cmd='read_verilog -sv leaf.v\nhierarchy -top '+top+'\nsynth -top '+top+' -noabc\nabc -script /OpenROAD-flow-scripts/flow/scripts/abc_speed.script '+libargs+' -dont_use *x1p*_ASAP7* -dont_use *xp*_ASAP7* -dont_use SDF* -dont_use ICG* -D 833\n'
cmd+='\n'.join('read_liberty -lib '+p for p in libs)+'\nstat -top '+top+'\nltp -noff\nwrite_verilog -noattr '+top+'.mapped.v\nwrite_json '+top+'.mapped.json\n'
Path(top+'.ys').write_text(cmd)
sta='read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef\nread_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef\n'+'\n'.join('read_liberty '+p for p in libs)+'\nread_verilog '+top+'.mapped.v\nlink_design '+top+'\ncreate_clock -name vclk -period 833\nset_input_delay 0 -clock vclk [all_inputs]\nset_output_delay 0 -clock vclk [all_outputs]\nset_load 1 [all_outputs]\nreport_checks -path_delay max -format full_clock_expanded -group_path_count 1\nreport_worst_slack -max\nexit\n'
Path(top+'.sta.tcl').write_text(sta)
PY
 if [ ! -f "$top.mapped.json" ]; then yosys -s "$top.ys" > "$top.map.log" 2>&1; fi
 yosys -p "read_json $top.mapped.json; hierarchy -top $top; clean -purge; write_verilog -noattr -noexpr $top.mapped.v" > "$top.clean.log" 2>&1
 openroad -exit "$top.sta.tcl" > "$top.sta.log" 2>&1
done
