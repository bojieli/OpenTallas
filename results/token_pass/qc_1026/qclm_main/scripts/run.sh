#!/bin/bash
# TOK-QK-QCLM 2026-10-26: QC per-layer stage set (259 pos cases: per layer resid1/resid2/silu/qk --rope rx, qkv/gu/od --arf,
# lm --arf, emb, LGPOS) on the CROM-aligned bound s8 slice row, BUILT FRESH from current main source (tree = git archive
# main, SOURCE_REVISION), instead of reusing the c1c42f554 binary (QCL 10-25: preprocessed text differed 434 lines from
# main, so current-main identity was NOT established).  Same vehicle, defines and runlist as QCL r1
# (intel2:/srv/opentallas-scratch2/claude/tok-qk-qcl/r1/run.sh + codex-qc-crom-row-1025/build_crom_row.sh).
set -u
E=$(cd "$(dirname "$0")" && pwd); T=$E/tree; W=$E/die
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH DV2_S8DIE=1 PYTHONDONTWRITEBYTECODE=1
verilator --version > $E/verilator_version.txt
DEFS="+define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM +define+OT_QFD_UP4_CK_ENTRIES +define+OT_S8_CROM_ALIGN"
JB=${JB:-48}
# 1. source list from main's dv_bench2 SRCS2 (DV2_S8DIE=1); record preprocessed text vs the QCL c1c42f554 binary's text
( cd $T && python3 - "$T" "$E" <<'PY'
import sys
from pathlib import Path
T,E=map(Path,sys.argv[1:]);sys.path.insert(0,str(T/'rtl/test/qwen_dv'));import dv_bench2 as B
files=list(dict.fromkeys(B.SRCS2))
missing=[x for x in files if not (T/x).exists()]
if missing:raise SystemExit('missing sources '+str(missing))
(E/'eq/sources_main.f').write_text('\n'.join(str(T/s) for s in files)+'\n')
PY
) || exit 5
verilator -E -P $DEFS -f $E/eq/sources_main.f > $E/eq/pp_main.sv 2> $E/eq/pp_main.err; echo "pp rc=$?" >> $E/eq/verdict.txt
[ -s $E/eq/pp_c1c.sv ] && { diff $E/eq/pp_c1c.sv $E/eq/pp_main.sv > $E/eq/pp.diff; echo "PP_DIFF_VS_C1C rc $? lines $(wc -l < $E/eq/pp.diff)" >> $E/eq/verdict.txt; }
# 2. fresh build (same flags as codex-qc-crom-row-1025/build_crom_row.sh; only -j/--build-jobs differ)
mkdir -p $W/build
t0=$(date +%s)
/usr/bin/time -v -o $E/build.time verilator --cc --exe --build -O1 -j $JB --build-jobs $JB --output-split 20000 --output-split-cfuncs 10000 --output-groups 192 \
 -CFLAGS -O0 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0' \
 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --x-assign 0 --x-initial 0 \
 $DEFS --top-module tb_qfd_dv2 --prefix Vtb -GMUT=0 -GN=12 -GMU_NU=4 -GFACE=3 -Mdir "$W/build/obj_n12" \
 "$T/rtl/test/qwen_dv/main2.cpp" -f "$E/eq/sources_main.f" > "$E/build.log" 2>&1
rc=$?; echo "BUILD rc=$rc $(( $(date +%s)-t0 )) s source=$(cat $E/SOURCE_REVISION)" | tee -a $E/eq/verdict.txt
[ $rc = 0 ] && [ -x $W/build/obj_n12/Vtb ] || exit 4
# 3. calibrations (main compiler, CROM profile) + full stage
echo "-GMU_NU=4 -GFACE=3 +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM +define+OT_QFD_UP4_CK_ENTRIES -Wno-WIDTHCONCAT +define+OT_S8_CROM_ALIGN" > $W/vflags.txt
cd $T
export DV_LOWER_VFLAGS="$(cat $W/vflags.txt)"
cal() { local out=$1; shift; local t0=$(date +%s); "$@" > "$out" 2>&1; local rc=$?; echo "rc=$rc" >> "$out"; echo "$(basename $(dirname $out))/$(basename $out) rc=$rc $(( $(date +%s)-t0 )) s"; return $rc; }
cal $W/build/slice_calibrate.out python3 rtl/test/qwen_dv/dv_lower_bench.py --work $W/build --calibrate || exit 6
cal $W/build/calibrate.out python3 rtl/test/qwen_dv/dv_lower_vec_bench.py --work $W/build --mode calibrate || exit 6
bash $T/tools/qwen_tokfunc/stage_stg_die.sh $E $E/stg_result.json $E/pos_runlist.txt --par ${PAR:-96}
python3 - $E/stgdie/result.json <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));print('QCLM_STG_DIE',r['verdict'],r['matched_pos'],'/',r['cases_total']);raise SystemExit(0 if r['verdict']=='PASS' else 1)
PY
