from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-hbm-tx-ff-size')
f=p/'rtl/ot_pdie_serdes_split.sv';s=f.read_text().replace('module ot_pdie_serdes_tx #','module ot_pdie_serdes_tx__fcore #');f.write_text(s)
f=p/'rtl/ot_pdie_serdes_tx__fshell.sv';s=f.read_text().replace('#(.ELA(2))','#(.ELA(2), .EFF(1))');f.write_text(s)
files=' '.join('/work/rtl/'+x.name for x in (p/'rtl').glob('*.sv'))
(p/'config.mk').write_text(f'''export DESIGN_NICKNAME = hbc_ot_pdie_serdes_tx_ff_size
export DESIGN_NAME = ot_pdie_serdes_tx
export PLATFORM = asap7
export VERILOG_FILES = {files}
export VERILOG_INCLUDE_DIRS = /work/rtl
export VERILOG_DEFINES = -DSYNTHESIS
export SDC_FILE = /work/constraint.sdc
export DIE_AREA = 0 0 285.12 207.36
export CORE_AREA = 4.32 4.32 280.8 203.04
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 1
export LEC_CHECK = 0
export SYNTH_CANONICALIZE_TCL = /work/ot_keep_regs.tcl
export CORNERS = tc
export TC_LIB_FILES = $(TC_NLDM_LIB_FILES)
override export LIB_FILES = $(TC_LIB_FILES)
''')
(p/'run_size.sh').write_text('''#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-hbm-tx-ff-size
docker run --rm --cpus=8 --memory=24g --memory-swap=24g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run NUM_CORES=8 synth' > synth.log 2>&1
''')
