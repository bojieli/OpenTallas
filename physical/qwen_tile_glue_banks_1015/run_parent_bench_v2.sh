#!/usr/bin/env bash
# v2 (paired interleaved W faces) parent bench: $1 MUT (TX mutants as v1), $2 out dir, $3 tb top (tb_parent_banked |
# tb_parent_banked_allbanks | tb_parent_banked_boot16), $4 "face" -> +define+OT_FACE_MUT (n_b capture rotated, must FAIL)
set -euo pipefail
mut=${1:-0}; out=${2:-sim_parent_m$mut}; top=${3:-tb_parent_banked}; fm=${4:-}
def=""; [[ "$fm" == face ]] && def="-DOT_FACE_MUT"
mkdir -p "$out"
verilator --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DOT_QWEN_LSL_FP1 $def -CFLAGS -O0 --output-split 20000 --output-split-cfuncs 2000 --top-module "$top" -GMUT="$mut" --Mdir "$out/obj" -f sim_sources.list > "$out/build.log" 2>&1
rc=0;"$out/obj/V$top" +OT_ROM_DIR=masks > "$out/run.log" 2>&1 || rc=$?
tail -5 "$out/run.log"
echo "RC=$rc"
