#!/bin/bash
set -euo pipefail
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
O=$1
mkdir -p "$O/rtl"
cp "$REPO/rtl/hdc/ot_sram_dline.sv" "$REPO/rtl/hdc/ot_sram_dline_nr.sv" "$O/rtl/"
cp "$REPO/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" "$O/rtl/"
cp "$REPO/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r0c0/ot_sram_1r1w_64x512_m1_r0c0.v" "$O/rtl/"
cp "$REPO/results/rtl/s81_quant_nr_2305/tb.sv" "$O/rtl/"
run() { verilator --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir "$O/obj_$1" "$O"/rtl/* > "$O/build_$1.log" 2>&1; "$O/obj_$1/Vtb" > "$O/run_$1.log" 2>&1; }
run positive
grep PASS "$O/run_positive.log"
python3 - "$O/rtl/ot_sram_dline_nr.sv" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1]);s=p.read_text();a='.r_addr_in(rp)';assert s.count(a)==1;p.write_text(s.replace(a,".r_addr_in(rp ^ 6'd1)"))
PY
if run address_mutant;then echo 'FAIL mutant escaped';exit 2;fi
grep -q 'DELAY_DIFF' "$O/run_address_mutant.log"
echo 'PASS wrong-address mutant CAUGHT in actual delay-line lockstep'
