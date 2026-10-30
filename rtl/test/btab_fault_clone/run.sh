#!/bin/bash
set -euo pipefail
w=/srv/opentallas-scratch2/claude/wt/codex-btab-fault-clone-1030
b=/srv/opentallas-scratch2/claude/codex-btab-fault-clone-1030
mkdir -p "$b"
s=$w/rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv
mem=$w/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
iverilog -g2012 -s tb -o "$b/normal.vvp" "$s" "$mem" "$w/rtl/test/btab_fault_clone/gold_original.sv" "$w/rtl/test/btab_fault_clone/tb.sv"
vvp "$b/normal.vvp" | tee "$b/normal.log"
python3 - "$s" "$b" <<'MUT'
import sys
from pathlib import Path
s=Path(sys.argv[1]).read_text();b=Path(sys.argv[2])
for name,a,z in [('wrongD','u_output (.ck(ck), .rst_n(rl1), .d(next_fault)','u_output (.ck(ck), .rst_n(rl1), .d(bs_bad_q)'),('wrongReset','u_output (.ck(ck), .rst_n(rl1)','u_output (.ck(ck), .rst_n(~rl1)')]:
 assert a in s;(b/(name+'.sv')).write_text(s.replace(a,z,1))
MUT
for m in wrongD wrongReset;do
 iverilog -g2012 -s tb -o "$b/$m.vvp" "$b/$m.sv" "$mem" "$w/rtl/test/btab_fault_clone/gold_original.sv" "$w/rtl/test/btab_fault_clone/tb.sv"
 if vvp "$b/$m.vvp" >"$b/$m.log" 2>&1;then echo "MUTANT_SURVIVED $m";exit 1;fi
 echo "MUTANT_CAUGHT $m $(head -n1 "$b/$m.log")"
done
