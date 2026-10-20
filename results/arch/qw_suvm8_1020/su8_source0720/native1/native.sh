#!/bin/bash
set -euo pipefail
cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib seq.lib
yosys -Q -s native.ys > native_map.log 2>&1
set +e
python3 native_census.py --netlist su8_mapped.v --top qfd_dv_s5_su8 --liberty cells.lib --out native.json > native.stdout 2>&1
NATIVE_RC=$?
python3 textbook_lint.py check --netlist su8_mapped.v --top qfd_dv_s5_su8 --out textbook.json > textbook.stdout 2>&1
TEXTBOOK_RC=$?
set -e
cat native.stdout
cat textbook.stdout
printf 'NATIVE_RC=%s TEXTBOOK_RC=%s\n' "$NATIVE_RC" "$TEXTBOOK_RC"
exit "$NATIVE_RC"
