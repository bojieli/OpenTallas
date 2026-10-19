#!/bin/bash
set -euo pipefail
lane=/srv/opentallas-scratch/claude/codex-s81-ctrl-bank64
prior=/srv/opentallas-scratch/claude/ref_gate/s81ctrl_rg2_sram-20261019-090615
mkdir -p "$lane/synth"
cp "$prior/routes/gate/work/orfs/config.mk" "$lane/synth/config.mk"
python3 - "$lane/synth/config.mk" <<'PYCONF'
import pathlib,sys
p=pathlib.Path(sys.argv[1]);s=p.read_text().replace('physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1','physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1').replace('= ot_sram_1r1w2c_16x546_m1','= ot_sram_1r1w2c_32x64_m1')
s=s.replace('/src/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/', '/bankmodel/')
s+='\nexport VERILOG_DEFINES = -DSYNTHESIS -DS81CTRL_SRAM_FIFO -DS81CTRL_SRAM_BANK64\n'
p.write_text(s)
PYCONF
docker run --rm -e LEC_CHECK=0 -v "$prior/src":/src:ro -v "$lane/rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g_sram.sv":/src/rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g_sram.sv:ro -v "$lane/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1":/bankmodel:ro -v "$lane/synth":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > "$lane/synth/driver.log" 2>&1
