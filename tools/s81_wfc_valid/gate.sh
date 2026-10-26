#!/bin/bash
set -euo pipefail
OUT=$1; MODE=${2:-gold}; mkdir -p "$OUT"
V=rtl/dsrom_sys/s81_ph/vm
SRC=${WFC_VALID_SOURCE:-$V/dsfd_vm_static_wfc.sv}
python3 - "$SRC" "$OUT/dut.sv" "$MODE" <<'PY'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text();m=sys.argv[3]
if m=='drop_read':s=s.replace(".s_v(1'b1)",'.s_v(f_wfc[0])')
elif m=='drop_write':s=s.replace(".s_v(1'b1)",'.s_v(f_wfc[528])')
elif m=='idle_request':s=s.replace('q_rv  = use_xv && xd_pin[528]','q_rv  = use_xv')
elif m!='gold':raise SystemExit('unknown mutant')
if m!='gold' and s==pathlib.Path(sys.argv[1]).read_text():raise SystemExit('mutant did not alter candidate')
pathlib.Path(sys.argv[2]).write_text(s)
PY
iverilog -g2012 -s tb_wfc_valid -o "$OUT/sim" "$OUT/dut.sv" "$V/ot_s81_vm_fault_transports.sv" "$V/ot_s81_vm_x34.sv" "$V/ot_s81_vm_x43.sv" tools/s81_wfc_valid/ref.sv tools/s81_wfc_valid/bench.sv
vvp -n "$OUT/sim"
