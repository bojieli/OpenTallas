#!/bin/bash
set -eu
python3 - <<'PYCFG'
from pathlib import Path
p=Path('work/config.mk');s=p.read_text();s=s.replace('export VERILOG_DEFINES = -DSYNTHESIS -DOT_BMUL_RSPLIT', 'export VERILOG_DEFINES = -DOT_BF_FOREP32 -DOT_BF_HELD_SRAM -DSYNTHESIS -DOT_BMUL_RSPLIT');s=s.replace('export VERILOG_FILES = ', 'export VERILOG_FILES = /src/physical/asap7_memory_macros/ot_sram_1r1w_128x32_m1/ot_sram_1r1w_128x32_m1_bb.v ')
s += '\nexport SYNTH_BLACKBOXES += ot_sram_1r1w_128x32_m1\nexport ADDITIONAL_LIBS += /src/physical/asap7_memory_macros/ot_sram_1r1w_128x32_m1/ot_sram_1r1w_128x32_m1_tt.lib\n'
s += '\nexport ADDITIONAL_LEFS += /src/physical/asap7_memory_macros/ot_sram_1r1w_128x32_m1/ot_sram_1r1w_128x32_m1.lef\nexport WC_LIB_FILES += /src/physical/asap7_memory_macros/ot_sram_1r1w_128x32_m1/ot_sram_1r1w_128x32_m1_tt.lib\nexport BC_LIB_FILES += /src/physical/asap7_memory_macros/ot_sram_1r1w_128x32_m1/ot_sram_1r1w_128x32_m1_ff.lib\n'
p.write_text(s)
PYCFG
docker run --rm -v "$PWD/src:/src:ro" -v "$PWD/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts && python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 synth"
