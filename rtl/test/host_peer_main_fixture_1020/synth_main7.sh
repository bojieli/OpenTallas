#!/bin/bash
set -eu
R=$PWD;mkdir -p synth_main7
python3 - <<'PYS'
from pathlib import Path
import json,shlex
r=Path.cwd();d=json.loads(Path('rtl/test/host_peer_main_fixture_1020/leaf_spec.json').read_text());n='ot_sram_1r1w_32x546_m1_p192_mir'
c='export DESIGN_NICKNAME = peer_leaf_census\nexport DESIGN_NAME = qkd_hr_core_peer_sram\nexport PLATFORM = asap7\nexport VERILOG_FILES = '+' '.join('/src/'+f for f in d['sources'])+'\nexport SDC_FILE = /src/rtl/test/host_peer_main_fixture_1020/recipe4_legacy/clock.sdc\nexport CORNER = WC\nexport ASAP7_USE_VT = RVT\nexport SYNTH_HIERARCHICAL = 0\nexport SYNTH_CANONICALIZE_TCL = /src/physical/common_flow/ot_keep_regs.tcl\nexport SYNTH_REPEATABLE_BUILD = 1\nexport SYNTH_MEMORY_MAX_BITS = 65536\nexport NUM_CORES = 4\nexport LEC_CHECK = 0\n'
line=next(x for x in Path('rtl/test/host_peer_main_fixture_1020/recipe4_legacy/kit.env').read_text().splitlines()if x.startswith('EXTRA=('));args=shlex.split(line[len('EXTRA=('):-1]);i=0;v={}
while i<len(args):
 if args[i]=='--orfs-var':
  k,value=args[i+1].split('=',1);v[k]=value;i+=2
 else:i+=1
v.update(OT_RST_LAND_COPIES='por_n=64,host_rst_n=64',OT_RST_LAND_FIRST_COPIES='por_n=2,host_rst_n=2',OT_RST_COPIES_MAX='32',OT_RST_COPIES_WIDE='1')
c+=''.join('export '+k+' = '+value+'\n' for k,value in v.items())
c+='export ADDITIONAL_LIBS = /src/physical/asap7_memory_macros/'+n+'/'+n+'_ss.lib\nexport SYNTH_BLACKBOXES = '+n+'\n'
Path('synth_main7/config.mk').write_text(c)
PYS
docker run --rm -v "$R:/src:ro" -v "$R/synth_main7:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base /work/results/asap7/peer_leaf_census/base/1_2_yosys.v' > synth_main7.log 2>&1
mkdir -p real5
docker run --rm -v "$R/real5:/libs" openroad/orfs:latest bash -lc 'cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_SS_nldm* /libs/'
libs=();for f in "$R"/real5/* "$R"/physical/asap7_memory_macros/*p192_mir/*_ss.lib;do libs+=(--liberty "$f");done
python3 rtl/test/host_peer_main_fixture_1020/coupon_tools/ref_tile/native_census.py --netlist synth_main7/results/asap7/peer_leaf_census/base/1_2_yosys.v --top qkd_hr_core_peer_sram "${libs[@]}" --out native_main7.json
