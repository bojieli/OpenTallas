#!/bin/bash
# Place-only structural prototype, while exact LEC runs on the same immutable
# mapped source/netlist in parallel. No CTS/route/adoption until both gates.
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-n59-2145-current2
K=$R/kit
# Fresh gen's RTL exactly matches the completed corrected-input synthesis.
python3 - "$R" <<'VERIFY'
import hashlib,json,sys
from pathlib import Path
r=Path(sys.argv[1]);expected=json.load(open(r/'source_hashes.json'))
for n,h in expected.items():assert hashlib.sha256((r/'kit/rtl'/n).read_bytes()).hexdigest()==h,n
VERIFY
sudo docker run --rm -v "$K:/work" openroad/orfs:latest bash -lc '
 set -euo pipefail
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 cd /OpenROAD-flow-scripts/flow
 M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 REMOVE_ABC_BUFFERS=1"
 python3 -I /work/sdc_lint.py /work --liberty $(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* | grep -v FAKE) > /work/sdc_lint.log 2>&1
 python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1
 python3 -I /work/selrange_gate.py /work > /work/selrange.log 2>&1
 N=/work/run/results/asap7/dp_native59/base/1_2_yosys.v
 python3 -I /work/port_bind_gate.py "$N" /work > /work/port_bind.log 2>&1
 python3 -I /work/face_guard.py "$N" --pins /work/pins.json --out /work/face_guard.json
 python3 -I /work/reg_fanout_gate.py "$N" --out /work/reg_fanout.json > /work/reg_fanout.log 2>&1
 # Reuse the byte-identical selected mapped checkpoint; rebuild OpenDB with
 # the native59 FF keep hook, then place with current batch1 pins/macros.
 $M run RUN_SCRIPT=/OpenROAD-flow-scripts/flow/scripts/synth_odb.tcl RUN_LOG_NAME_STEM=1_synth_n59keep
 $M -o /work/run/results/asap7/dp_native59/base/1_synth.odb place
 '
