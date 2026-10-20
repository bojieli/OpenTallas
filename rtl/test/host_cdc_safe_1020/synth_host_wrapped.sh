#!/bin/bash
set -eu
R=$PWD;mkdir -p "$R/synth_host_wrapped1"
python3 - <<'PY2'
from pathlib import Path
r=Path.cwd();import json
files=json.loads(Path('rtl/test/host_cdc_safe_1020/host_sram1.json').read_text())['sources']
c='export DESIGN_NICKNAME = host_cdc_host_census\nexport DESIGN_NAME = qkd_hr_cdc_host_sram\nexport PLATFORM = asap7\nexport VERILOG_FILES = '+' '.join('/src/'+f for f in files)+'\nexport SDC_FILE = /work/constraint.sdc\nexport CORNER = WC\nexport ASAP7_USE_VT = RVT\nexport SYNTH_HIERARCHICAL = 0\nexport SYNTH_CANONICALIZE_TCL = /src/physical/common_flow/ot_keep_regs.tcl\nexport SYNTH_REPEATABLE_BUILD = 1\nexport SYNTH_MEMORY_MAX_BITS = 65536\nexport NUM_CORES = 4\nexport LEC_CHECK = 0\n'
import shlex
K=r/'physical/ref_tile/qkd_hr_cdc_host_sram1/kit.env'
line=next(x for x in K.read_text().splitlines() if x.startswith('EXTRA=('))
args=shlex.split(line[len('EXTRA=('):-1]);i=0
while i<len(args):
 if args[i]=='--orfs-var':
  key,value=args[i+1].split('=',1);c+='export '+key+' = '+value+'\n';i+=2
 else:i+=1
names=['ot_sram_1r1w_32x546_m1_p192_mir','ot_sram_1r1w2c_32x546_m1_p192_mir','ot_sram_1r1w_32x64_m1_p192_mir']
c+='export ADDITIONAL_LIBS = '+' '.join('/src/physical/asap7_memory_macros/'+n+'/'+n+'_ss.lib' for n in names)+'\n'
c+='export SYNTH_BLACKBOXES = '+' '.join(names)+'\n'
Path('synth_host_wrapped1/config.mk').write_text(c)
Path('synth_host_wrapped1/constraint.sdc').write_text('create_clock -name ck_core -period 833.333 [get_ports ck_core]\ncreate_clock -name ck_host -period 1000 [get_ports ck_host]\n')
PY2
docker run --rm -v "$R:/src:ro" -v "$R/synth_host_wrapped1:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base /work/results/asap7/host_cdc_host_census/base/1_2_yosys.v' > "$R/synth_host_wrapped1.log" 2>&1
python3 tools/textbook_lint.py check --netlist "$R/synth_host_wrapped1/results/asap7/host_cdc_host_census/base/1_2_yosys.v" --out "$R/census_host_wrapped1.json" --mode warn --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 reset_ports=host_rst_n

mkdir -p "$R/loaded_real5"
docker run --rm -v "$R/loaded_real5:/libs" openroad/orfs:latest bash -lc 'cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_SS_nldm* /libs/'
libs=();for f in "$R"/loaded_real5/* "$R"/physical/asap7_memory_macros/*p192_mir/*_ss.lib;do libs+=(--liberty "$f");done
python3 tools/ref_tile/native_census.py --netlist "$R/synth_host_wrapped1/results/asap7/host_cdc_host_census/base/1_2_yosys.v" --top qkd_hr_cdc_host_sram "${libs[@]}" --out "$R/native_host_wrapped1_real5.json"
