#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/codex/lg-sfu14-slew-repair-1015
src=/srv/opentallas-scratch/codex/lg-sfu14-native-route-1015/src
cd "$src"
odbbase=$(dirname "$(find "$base/work/results/asap7" -name 6_final.odb -print -quit)")
python3 tools/closure_loop/ck_insertion.py --base "$odbbase" --clock clk --all-clocks --raw-source --routed --route-corner TC --output "$base/ck_routed.json" > "$base/ck_routed.log" 2>&1
cat > "$base/final_pin_dump.tcl" <<'TCL'
read_db /base/6_final.odb
source /src/tools/fp_margin_lint.tcl
ot_fp_lint_dump /out/final_actual_pin_pg.json
exit
TCL
docker run --rm -v "$odbbase:/base:ro" -v "$src:/src:ro" -v "$base:/out" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/final_pin_dump.tcl' > "$base/final_pin_dump.log" 2>&1
python3 rtl/hbm_accel/generic/vm/static/physical/check_native_bank_pin_pg.py "$base/final_actual_pin_pg.json" "$odbbase/native_bank_pin_coordinates.tsv" --out "$base/final_pin_audit.json" > "$base/final_pin_audit.log"
python3 tools/ref_tile/ref_tile.py export --orfs-dir "$base/work" --kit physical/ref_tile/vm_lg_bank_sfu14_static_1015 --out "$base/views/hfd_vm_lg_sfu14" > "$base/export.log" 2>&1
