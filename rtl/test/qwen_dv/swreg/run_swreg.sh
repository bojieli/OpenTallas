#!/usr/bin/env bash
# HARD-QC-FORMS-1: lock-step bench of the registered sram_delay output (OT_QC_SWREG, 0 cycles).  From the repository root:
#   bash rtl/test/qwen_dv/swreg/run_swreg.sh OUTDIR      expect base PASS, +N=1 FAIL, MUT FAIL
set -u; OUT=$1; mkdir -p "$OUT"; D=rtl/test/qwen_dv/swreg; rc=0
python3 -I - > "$OUT/dut.sv" <<'PY'
import re
s = open("rtl/qwen_dv/s5/s8/qfd_dv_s8_station_safe.sv").read()
m = re.search(r"module qfd_dv_s8s_sram_delay #.*?endmodule\n", s, re.S); print(m.group(0))
PY
iverilog -g2012 -DSYNTHESIS -o "$OUT/tb" $D/tb_swreg.sv "$OUT/dut.sv" > "$OUT/build.log" 2>&1 || { echo BUILD FAIL; cat "$OUT/build.log"; exit 1; }
iverilog -g2012 -DSYNTHESIS -DTB_MUT -o "$OUT/tb_mut" $D/tb_swreg.sv "$OUT/dut.sv" > "$OUT/build_mut.log" 2>&1 || { echo BUILD FAIL; exit 1; }
exp() { r=$(grep -o 'SWREG_LOCKSTEP [A-Z]*' "$2" | head -1); echo "$1: ${r:-NO_RESULT} (expected $3)"; [ "$r" = "SWREG_LOCKSTEP $3" ] || rc=1; }
vvp "$OUT/tb" > "$OUT/base.log" 2>&1;       exp "base N=0" "$OUT/base.log" PASS
vvp "$OUT/tb" +N=1 > "$OUT/n1.log" 2>&1;    exp "wrong N=1" "$OUT/n1.log" FAIL
vvp "$OUT/tb_mut" > "$OUT/mut.log" 2>&1;    exp "MUT read address" "$OUT/mut.log" FAIL
grep SWREG_LOCKSTEP "$OUT/base.log"; echo "RUN_SWREG rc=$rc"; exit $rc
