#!/usr/bin/env bash
# Same-cycle full32-entry queue policy versus historical implementation.
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out/tmp"
export TMPDIR="$(cd "$out/tmp" && pwd)"
src=rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv
tb=rtl/hbm_accel/loader/service_native/tb_hbm_pc_physical_write_act.sv
iverilog -g2012 -s tb -o "$out/positive.vvp" "$src" "$tb" > "$out/positive.build.log" 2>&1
vvp "$out/positive.vvp" > "$out/positive.log" 2>&1
grep 'PC_PHYSICAL_WRITE_ACT PASS' "$out/positive.log"
python3 - "$src" "$out/age_mutant.sv" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
old='wq_act_physical[ai] && !(|(wq_older[ai*WQ +: WQ] & wq_act_physical))'
new='wq_act_physical[ai] && (|(wq_older[ai*WQ +: WQ] & wq_act_physical))'
assert s.count(old)==1
Path(sys.argv[2]).write_text(s.replace(old,new))
PY
iverilog -g2012 -s tb -o "$out/age_mutant.vvp" "$out/age_mutant.sv" "$tb" > "$out/age_mutant.build.log" 2>&1
if vvp "$out/age_mutant.vvp" > "$out/age_mutant.log" 2>&1; then
  echo 'physical write ACT age mutant survived'
  exit 1
fi
grep 'physical_write_act candidate mismatch' "$out/age_mutant.log"
echo 'PC_PHYSICAL_WRITE_ACT_GATE PASS (historical same-cycle policy; reversed age mutant rejected)'
