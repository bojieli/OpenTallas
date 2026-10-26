#!/bin/bash
set -eu
P=$(realpath -m "${1:?usage: run.sh OUTPUT [SOURCE_TREE]}")
T=$(realpath "${2:-$(dirname "$0")/../../../..}")
mkdir -p "$P"
cp "$T/rtl/qwen_dv/qfd_dv_head_safe1.sv" "$T/rtl/test/qwen_dv/s8_memory_align/tb_s8_memalign.sv" "$P/"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH PYTHONDONTWRITEBYTECODE=1
test ! -e "$P/run_clean.log" || { echo "Use a fresh OUTPUT to preserve old verdicts"; exit 2; }
python3 - "$T" "$P" <<'PY'
import sys
from pathlib import Path
T,P=map(Path,sys.argv[1:]);sys.path.insert(0,str(T/'rtl/test/qwen_dv'));import dv_bench2 as B
src=list(dict.fromkeys(B.SRCS2+B.XSRCS+['physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v']))
(P/'sources.f').write_text('\n'.join(str(T/s) for s in src if not s.endswith('/qfd_dv_head_safe1.sv'))+'\n')
PY
for M in clean mutant; do
 D=;test "$M" = clean || D=+define+OT_S8_CROM_ALIGN_MUTANT
 verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 $D --top-module tb_s8_memalign -f "$P/sources.f" "$P/qfd_dv_head_safe1.sv" "$P/tb_s8_memalign.sv" -Mdir "$P/obj_$M" > "$P/build_$M.log" 2>&1 || { tail -35 "$P/build_$M.log";exit 1; }
 "$P/obj_$M/Vtb_s8_memalign" > "$P/run_$M.log" 2>&1
 tail -8 "$P/run_$M.log"
done
