#!/bin/bash
set -eu
cd "$(dirname "$0")/../.."
OUT=${1:?provide unique result directory}; mkdir -p "$OUT"
Y=${YOSYS:-$HOME/.local/opentallas-tools/bin/yosys}
SRC=rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv
for V in control mutant; do
 D=; [ "$V" != mutant ] || D="-D MUTANT"
 if "$Y" -Q -T -p "read_verilog -sv $D $SRC tools/qwen_fault_split/miter.sv; hierarchy -top fault_split_miter; proc; flatten; opt; async2sync; opt; sat -seq 4 -tempinduct -prove eq 1 -set-init-zero -verify" > "$OUT/$V.log" 2>&1; then
  RC=0
 else RC=$?; fi
 echo "$V rc=$RC"
 if [ "$V" = control ]; then [ "$RC" = 0 ]; else [ "$RC" != 0 ]; grep -q "proof did fail" "$OUT/$V.log"; fi
done
echo "PASS sequential induction; mutant rejected"
