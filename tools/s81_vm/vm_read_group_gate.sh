#!/bin/bash
# Fleet-only via ot-run: vm_read_group_gate.sh SRC OUT
set -euo pipefail
SRC=$1; OUT=$2; mkdir -p "$OUT"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for cfg in 16:0 2:0 16:1; do
 n=${cfg%:*}; m=${cfg#*:}; B="$OUT/obj_${n}_${m}"
 "$VL" --binary --timing -Wno-fatal --top-module tb_dsfd_vm_read_group -GNR="$n" -GMUT_EARLY="$m" \
  -Mdir "$B" -j 1 "$SRC/rtl/test/s81_client_transport_diagnostic/dsfd_vm_read_group.sv" \
  "$SRC/rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_read_group.sv" > "$OUT/build_${n}_${m}.log" 2>&1
 "$B/Vtb_dsfd_vm_read_group" > "$OUT/run_${n}_${m}.log" 2>&1
 if [ "$m" = 0 ]; then grep -qx PASS "$OUT/run_${n}_${m}.log"; else grep -qx FAIL "$OUT/run_${n}_${m}.log"; fi
 grep '^RESULT' "$OUT/run_${n}_${m}.log"
done
echo VM_READ_GROUP_GATE_PASS
