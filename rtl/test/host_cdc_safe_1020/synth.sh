#!/bin/bash
set -eu
R=$PWD;mkdir -p "$R/synth"
python3 - <<'PY2'
from pathlib import Path
r=Path.cwd();files=Path('rtl/test/host_cdc_safe_1020/sources.f').read_text().splitlines()
files=[f for f in files if not f.endswith('tb_safe.sv')]
files=[f.replace('.v','_bb.v') if 'asap7_memory_macros/' in f else f for f in files]
c='export DESIGN_NICKNAME = host_cdc_safe_census\nexport DESIGN_NAME = ot_host_die_cdc_sram\nexport PLATFORM = asap7\nexport VERILOG_FILES = '+' '.join('/src/'+f for f in files)+'\nexport SDC_FILE = /work/constraint.sdc\nexport CORNER = WC\nexport ASAP7_USE_VT = RVT\nexport SYNTH_HIERARCHICAL = 0\nexport SYNTH_REPEATABLE_BUILD = 1\nexport SYNTH_MEMORY_MAX_BITS = 65536\nexport NUM_CORES = 4\nexport LEC_CHECK = 0\n'
Path('synth/config.mk').write_text(c)
Path('synth/constraint.sdc').write_text('create_clock -name wclk -period 833.333 [get_ports wclk]\ncreate_clock -name rclk -period 1043 [get_ports rclk]\n')
PY2
docker run --rm -v "$R:/src:ro" -v "$R/synth:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > "$R/synth.log" 2>&1
python3 tools/textbook_lint.py check --netlist "$R/synth/results/asap7/host_cdc_safe_census/base/1_2_yosys.v" --out "$R/census.json" --mode warn
