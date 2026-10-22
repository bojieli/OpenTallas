#!/bin/bash
set -eu
R=$PWD;mkdir -p synth_cmd8
python3 - <<'PYS'
from pathlib import Path
p=Path('rtl/test/host_peer_main_fixture_1020/historical/rtl/qwen_sys/host_cluster_20261017/peer_pd/qkd_host_ctrl_token_service_packet_collected_pd2.sv');s=p.read_text().replace('module qkd_host_ctrl_token_service_packet_collected_pd2 #','module qkd_host_cmd_read32 #').replace('STRAPPED=0','STRAPPED=1').replace('ENABLE_SERVICE=0','ENABLE_SERVICE=1').replace('ENABLE_TOKEN=0','ENABLE_TOKEN=1').replace('CMD_READ32=0','CMD_READ32=1');Path('synth_cmd8/top.sv').write_text(s)
c='export DESIGN_NICKNAME = peer_cmd_read32\nexport DESIGN_NAME = qkd_host_cmd_read32\nexport PLATFORM = asap7\nexport VERILOG_FILES = /work/top.sv\nexport SDC_FILE = /work/constraint.sdc\nexport CORNER = WC\nexport ASAP7_USE_VT = RVT\nexport SYNTH_HIERARCHICAL = 0\nexport SYNTH_CANONICALIZE_TCL = /src/physical/common_flow/ot_keep_regs.tcl\nexport SYNTH_REPEATABLE_BUILD = 1\nexport NUM_CORES = 4\nexport LEC_CHECK = 0\n'
Path('synth_cmd8/config.mk').write_text(c);Path('synth_cmd8/constraint.sdc').write_text('create_clock -name ck -period 833.333 [get_ports ck]\n')
PYS
docker run --rm -v "$R:/src:ro" -v "$R/synth_cmd8:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base /work/results/asap7/peer_cmd_read32/base/1_2_yosys.v' > synth_cmd8.log 2>&1
mkdir -p real5
docker run --rm -v "$R/real5:/libs" openroad/orfs:latest bash -lc 'cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_SS_nldm* /libs/'
libs=();for f in "$R"/real5/*;do libs+=(--liberty "$f");done
python3 rtl/test/host_peer_main_fixture_1020/coupon_tools/ref_tile/native_census.py --netlist synth_cmd8/results/asap7/peer_cmd_read32/base/1_2_yosys.v --top qkd_host_cmd_read32 "${libs[@]}" --out native_cmd8.json
