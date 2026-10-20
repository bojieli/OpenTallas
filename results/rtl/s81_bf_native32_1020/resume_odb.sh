#!/bin/bash
set -eu
python3 - <<'PYCFG'
from pathlib import Path
p=Path('work/config.mk');s=p.read_text();base='/src/physical/asap7_memory_macros/ot_sram_1r1w_128x32_m1/ot_sram_1r1w_128x32_m1'
s+='\nexport ADDITIONAL_LEFS += '+base+'.lef\nexport WC_LIB_FILES += '+base+'_tt.lib\nexport BC_LIB_FILES += '+base+'_ff.lib\n';p.write_text(s)
PYCFG
docker run --rm -v "$PWD/src:/src:ro" -v "$PWD/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts && python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && make -o /work/results/asap7/opentallas_ot_v41_bf_col_asap7_ref_gate/base/1_2_yosys.v DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 synth"
