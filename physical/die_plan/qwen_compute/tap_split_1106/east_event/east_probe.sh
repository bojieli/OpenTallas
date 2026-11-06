#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc-tapsplit-east-1106
K=/srv/opentallas-scratch2/claude/codex-wave-1105/runs/qwen_compute/kit-wave/qwen_compute/efdb36e864/items/sle_su_c/gen/sle_su_c
python3 - "$K" "$R" <<'PY'
import sys
from pathlib import Path
K,R=map(Path,sys.argv[1:]);s=(K/'hold_gate.tcl').read_text().split('set w [sta::time_sta_ui',1)[0];s=s.replace('[file dirname [file normalize [info script]]]','/work');(R/'prefix.tcl').write_text(s)
PY
docker run --rm --cpus=2 --memory=12g -v "$K:/work:ro" -v "$R:/out" -e OT_VCLK_FF=202.5 -e OT_HOLD_IN_MIN=-85 -e OT_HOLD_OUT_MIN=95 -e OT_TAP_WINDOW=120 -e LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl -e ODB=/work/run/results/asap7/dp_sle_su_c/base/4_cts.odb -e SDC=/work/run/results/asap7/dp_sle_su_c/base/4_cts.sdc --entrypoint bash openroad/orfs:asap7lock -c 'L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM; PLIBS="";for n in AO INVBUF OA SEQ SIMPLE;do P=$(find "$L" -maxdepth 1 -name "asap7sc7p5t_${n}_RVT_FF_nldm*" ! -name "*250407*" | sort | head -1); PLIBS="$PLIBS $P";done; export PLIBS="$PLIBS $(find /work/macros -maxdepth 1 -name "*_ff.lib" | sort | tr "\n" " ")"; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/east_probe.tcl' > "$R/probe.log" 2>&1
