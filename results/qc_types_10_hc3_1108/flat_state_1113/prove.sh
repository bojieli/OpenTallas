#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc-hc3-1113
S=$R/input
D=$S/rtl/qwen_sys/dvm_20261014
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
[ -x "$Y" ] || Y=$(find "$HOME/.local/opentallas-tools/yosys-0.68" -maxdepth 3 -type f -name yosys | head -1)
mkdir -p "$R/proof"
python3 -I - "$R" <<'PY'
from pathlib import Path
import sys
r=Path(sys.argv[1]);d=r/'proof'
for a,b in [('source/original_fo32.sv','original_none.sv'),('source/ot_qfd_xs_leaf_fo32.sv','fixed_none.sv')]:
 (d/b).write_text('`default_nettype none\n'+(r/a).read_text())
PY
set +e
"$Y" -q -p "read_verilog -sv $R/proof/original_none.sv $D/ot_qfd_xs_leaf_fo32_w.sv; hierarchy -check -top ot_qfd_xs_leaf_fo32_w" > "$R/proof/yosys_original.log" 2>&1
oldrc=$?
"$Y" -q -p "read_verilog -sv $R/proof/fixed_none.sv $D/ot_qfd_xs_leaf_fo32_w.sv; hierarchy -check -top ot_qfd_xs_leaf_fo32_w" > "$R/proof/yosys_fixed.log" 2>&1
newrc=$?
set -e
printf 'YOSYS original_rc=%s fixed_rc=%s\n' "$oldrc" "$newrc"
[ "$oldrc" != 0 ] && [ "$newrc" = 0 ]
sed 's/ot_qfd_xs_leaf_fo32 #(.GRP(GRP),.NG(NG),.NQ(NQ),.MUT(MUT)) dut/ot_qfd_xs_leaf_fo32_w #(.NCH(4),.FILL_PIPE(1),.READ_PIN_PIPE(1),.MUT(MUT)) dut/' "$D/tb_qfd_xs_leaf_fo32.sv" > "$R/proof/tb_w.sv"
for mode in base mutant; do
 extra=(); [ "$mode" != mutant ] || extra=(-GMUT=2)
 mkdir -p "$R/proof/$mode"
 "$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --x-assign 0 --x-initial 0 --top-module tb_qfd_xs_leaf_fo32 --Mdir "$R/proof/$mode/obj" -GSEED=7 -GNOPS=20000 "${extra[@]}" "$R/proof/tb_w.sv" "$D/ot_qfd_xs_leaf_fo32_w.sv" "$R/source/ot_qfd_xs_leaf_fo32.sv" "$D/ot_qfd_xslice.sv" "$S/rtl/hdc/ot_hdc_delay.sv" -o tb > "$R/proof/$mode/build.log" 2>&1
 set +e
 "$R/proof/$mode/obj/tb" > "$R/proof/$mode/run.log" 2>&1
 rc=$?
 set -e
 printf 'LOCKSTEP %s rc=%s\n' "$mode" "$rc"
 tail -n 3 "$R/proof/$mode/run.log"
 if [ "$mode" = base ]; then [ "$rc" = 0 ]; else [ "$rc" != 0 ]; fi
done
printf 'HC3_FLAT_STATE_PROOF_PASS\n'
