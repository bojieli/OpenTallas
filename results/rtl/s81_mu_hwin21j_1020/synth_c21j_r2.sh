#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/claude/ref_gate/dsdv_mu_hwin_c21h-20261019-213545
lane=/srv/opentallas-scratch/claude/codex-s81-hwin21j-r2-1020
work=/srv/opentallas-scratch/claude/codex-hwin-native-1020/synth_c21j_r2
mkdir -p "$work"
cp "$base/routes/gate/work/orfs/config.mk" "$work/config.mk"
cp "$base/routes/gate/work/orfs/constraint.sdc" "$work/constraint.sdc"
python3 - "$work/config.mk" <<'PYCODE'
import sys
from pathlib import Path
p=Path(sys.argv[1]);s=p.read_text();s=s.replace('export VERILOG_TOP_PARAMS =','export VERILOG_TOP_PARAMS = SAFE_NATIVE 1',1).replace('export SYNTH_KEEP_MODULES =','export SYNTH_KEEP_MODULES = dsdv_mu_hwin_capture_1019_cfg_accept dsdv_mu_hwin_capture_1019_early_current_hit',1);p.write_text(s)
PYCODE
sha256sum "$lane/rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin_capture_1019.sv" "$lane/rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin_capture_early_1019.sv" "$work/config.mk" > "$work/SOURCE_SHA256"
docker run --rm -v "$base/src:/src:ro" -v "$lane/rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin_capture_1019.sv:/src/rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin_capture_1019.sv:ro" -v "$lane/rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin_capture_early_1019.sv:/src/rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin_capture_early_1019.sv:ro" -v "$work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 synth' > "$work/synth.log" 2>&1
netlist="$work/results/asap7/opentallas_dsdv_mu_hwin_capture_1019_asap7_ref_gate/base/1_2_yosys.v"
python3 mapped_census.py --tool textbook_lint.py --netlist "$netlist" --top dsdv_mu_hwin_capture_1019 --out c21j_r2_mapped_native.json
printf 'SYNTH_CENSUS_RC=0\n'
