#!/bin/bash
# KV-PEER12 10-20: synthesis (ORFS Yosys, the PEER leaf census flow of ../synth_main7.sh) of the MU 1 PEER composition
# qkd_hr_core_peer_sram_mu (sources.txt) -> synth_mu/results/asap7/peer_mu_census/base/1_2_yosys.v + native census.
# usage (repo root): bash rtl/test/host_peer_main_fixture_1020/mu_sram/synth_mu.sh
set -eu
R=$PWD;D=rtl/test/host_peer_main_fixture_1020;mkdir -p synth_mu
python3 - <<'PYS'
from pathlib import Path
import shlex
D='rtl/test/host_peer_main_fixture_1020';n='ot_sram_1r1w_32x546_m1_p192_mir'
srcs=[l for l in Path(D+'/mu_sram/sources.txt').read_text().split() if l]
c='export DESIGN_NICKNAME = peer_mu_census\nexport DESIGN_NAME = qkd_hr_core_peer_sram_mu\nexport PLATFORM = asap7\nexport VERILOG_FILES = '+' '.join('/src/'+f for f in srcs)+'\nexport SDC_FILE = /src/'+D+'/recipe4_legacy/clock.sdc\nexport CORNER = WC\nexport ASAP7_USE_VT = RVT\nexport SYNTH_HIERARCHICAL = 0\nexport SYNTH_CANONICALIZE_TCL = /src/physical/common_flow/ot_keep_regs.tcl\nexport SYNTH_REPEATABLE_BUILD = 1\nexport SYNTH_MEMORY_MAX_BITS = 65536\nexport NUM_CORES = 4\nexport LEC_CHECK = 0\n'
line=next(x for x in Path(D+'/recipe4_legacy/kit.env').read_text().splitlines() if x.startswith('EXTRA=('));args=shlex.split(line[len('EXTRA=('):-1]);i=0;v={}
while i<len(args):
 if args[i]=='--orfs-var':
  k,value=args[i+1].split('=',1);v[k]=value;i+=2
 else:i+=1
v.update(OT_RST_LAND_COPIES='por_n=64,host_rst_n=64',OT_RST_LAND_FIRST_COPIES='por_n=2,host_rst_n=2',OT_RST_COPIES_MAX='32',OT_RST_COPIES_WIDE='1')
c+=''.join('export '+k+' = '+value+'\n' for k,value in v.items())
c+='export ADDITIONAL_LIBS = /src/physical/asap7_memory_macros/'+n+'/'+n+'_ss.lib\nexport SYNTH_BLACKBOXES = '+n+'\n'
Path('synth_mu/config.mk').write_text(c)
PYS
docker run --rm -v "$R:/src:ro" -v "$R/synth_mu:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base /work/results/asap7/peer_mu_census/base/1_2_yosys.v' > synth_mu.log 2>&1
mkdir -p real5
docker run --rm -v "$R/real5:/libs" openroad/orfs:latest bash -lc 'cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_SS_nldm* /libs/'
libs=();for f in "$R"/real5/* "$R"/physical/asap7_memory_macros/*p192_mir/*_ss.lib;do libs+=(--liberty "$f");done
python3 $D/coupon_tools/ref_tile/native_census.py --netlist synth_mu/results/asap7/peer_mu_census/base/1_2_yosys.v --top qkd_hr_core_peer_sram_mu "${libs[@]}" --out native_mu.json
sha256sum synth_mu/results/asap7/peer_mu_census/base/1_2_yosys.v
