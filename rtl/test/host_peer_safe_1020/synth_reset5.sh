#!/bin/bash
set -eu
R=$PWD;mkdir -p synth_reset5
python3 - <<'PYS'
from pathlib import Path
p=Path('rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_link.sv')
Path('synth_reset5/top.sv').write_text(p.read_text().replace('module qkd_host_peer_link #','module qkd_host_peer_link_safe #').replace('parameter integer SAFE_SRAM=0','parameter integer SAFE_SRAM=1'))
n='ot_sram_1r1w_32x546_m1_p192_mir';m='/src/physical/asap7_memory_macros/'+n+'/'+n
c='export DESIGN_NICKNAME = peer_safe_census\nexport DESIGN_NAME = qkd_host_peer_link_safe\nexport PLATFORM = asap7\nexport VERILOG_FILES = /work/top.sv /src/rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_sram_head.sv '+m+'_bb.v\nexport SDC_FILE = /work/constraint.sdc\nexport CORNER = WC\nexport ASAP7_USE_VT = RVT\nexport SYNTH_HIERARCHICAL = 0\nexport SYNTH_CANONICALIZE_TCL = /src/physical/common_flow/ot_keep_regs.tcl\nexport SYNTH_REPEATABLE_BUILD = 1\nexport NUM_CORES = 4\nexport LEC_CHECK = 0\nexport ADDITIONAL_LIBS = '+m+'_ss.lib\nexport SYNTH_BLACKBOXES = '+n+'\n'
c+='export OT_PIN_REGS = 0\nexport OT_PIN_REGS_CLOCK = ck\nexport OT_PIN_REGS_RESET_PORTS = rst_n\nexport OT_PIN_REGS_RESET = ^(rst_n)$\nexport OT_RST_LAND = 1\nexport OT_RST_LAND_STAGES = 2\nexport OT_RST_LAND_COPIES = rst_n=8\nexport OT_RST_LAND_FIRST_COPIES = rst_n=1\nexport OT_RST_COPIES_MAX = 32\nexport OT_RST_COPIES_WIDE = 1\n'
Path('synth_reset5/config.mk').write_text(c);Path('synth_reset5/constraint.sdc').write_text('create_clock -name ck -period 833.333 [get_ports ck]\n')
PYS
docker run --rm -v "$R:/src:ro" -v "$R/synth_reset5:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base /work/results/asap7/peer_safe_census/base/1_2_yosys.v' > synth_reset5.log 2>&1
mkdir -p real5
docker run --rm -v "$R/real5:/libs" openroad/orfs:latest bash -lc 'cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_SS_nldm* /libs/'
libs=();for f in "$R"/real5/* "$R"/physical/asap7_memory_macros/*p192_mir/*_ss.lib;do libs+=(--liberty "$f");done
python3 coupon_tools/ref_tile/native_census.py --netlist synth_reset5/results/asap7/peer_safe_census/base/1_2_yosys.v --top qkd_host_peer_link_safe "${libs[@]}" --out native_reset5.json
