#!/bin/bash
set -eu
P=$(cd "$(dirname "$0")" && pwd)
T=$P/tree
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH DV2_S8DIE=1 PYTHONDONTWRITEBYTECODE=1
cd "$T"
python3 - "$T" "$P" <<'PY'
import sys
from pathlib import Path
T,P=map(Path,sys.argv[1:]);sys.path.insert(0,str(T/'rtl/test/qwen_dv'));import dv_bench2 as B
files=list(dict.fromkeys(B.SRCS2))
missing=[x for x in files if not (T/x).exists()]
if missing:raise SystemExit('missing sources '+str(missing))
(P/'sources.f').write_text('\n'.join(str(T/s) for s in files)+'\n')
PY
/usr/bin/time -v -o "$P/build.time" verilator --cc --exe --build -O1 -j 32 --build-jobs 32 --output-split 20000 --output-split-cfuncs 10000 --output-groups 192 \
 -CFLAGS -O0 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0' \
 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --x-assign 0 --x-initial 0 \
 +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM +define+OT_QFD_UP4_CK_ENTRIES +define+OT_S8_CROM_ALIGN \
 --top-module tb_qfd_dv2 --prefix Vtb -GMUT=0 -GN=12 -GMU_NU=4 -GFACE=3 -Mdir "$P/obj_n12" \
 "$T/rtl/test/qwen_dv/main2.cpp" -f "$P/sources.f" > "$P/build.log" 2>&1
printf 'BUILD PASS source='; cat "$P/SOURCE_REVISION"
