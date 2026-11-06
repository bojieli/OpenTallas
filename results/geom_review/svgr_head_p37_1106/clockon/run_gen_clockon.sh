#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
TASK_ROOT=$PWD
TOOL="$TASK_ROOT/wt/physical/die_plan/hbm_arch_cores"
python3 "$TOOL/gen_core_kit_hbm.py" --views "$TASK_ROOT/views_own.json" --view ot_svgr_own@2054dcac0c09 --recipe-key ot_svgr_own__headtail --out "$TASK_ROOT/kits_clockon" --corner TC --sigmax M5 --face-shell on --clock-taps density --clock-tap-sinks 1250 --clock-tap-dmax 80 --tag headtail_p37_clockon --clock-pin-entry on
python3 "$TASK_ROOT/render_clockon.py"
