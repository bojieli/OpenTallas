#!/bin/bash
set -euo pipefail
O=$1; M=${2:-0}; T=$(pwd);mkdir -p "$O"
python3 - "$T" "$O" <<'PY2'
import sys
from pathlib import Path
T,O=map(Path,sys.argv[1:]);sys.path.insert(0,str(T/'rtl/test/qwen_dv'));import dv_bench2 as B
src=list(dict.fromkeys(B.SRCS2+B.XSRCS+['physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v']))
(O/'sources.f').write_text('\n'.join(str(T/s) for s in src if not s.endswith('/qfd_dv_head_safe1.sv'))+'\n')
PY2
D=; [ "$M" = 0 ] || D=+define+OT_MIF_HEAD_MUTANT
$HOME/.local/opentallas-tools/bin/verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 $D --top-module tb_s8_memalign -f "$O/sources.f" rtl/qwen_dv/qfd_dv_head_safe1.sv tools/qwen_dv/mif1309/tb_mif_head.sv -Mdir "$O/obj" > "$O/build.log" 2>&1
"$O/obj/Vtb_s8_memalign" > "$O/run.log" 2>&1
cat "$O/run.log"
if [ "$M" = 0 ]; then grep -q 'MIF_HEAD PASS' "$O/run.log"; else grep -q 'MIF_HEAD FAIL' "$O/run.log";fi
