#!/bin/bash
# Fleet only. Source root must be the frozen dedf4c794 transport packet plus this bench.
set -eu
OUT=${1:?output}; shift
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"
SOURCES=rtl/test/qwen_split/mu_context_real_link_sources.f
sha256sum $(cat "$SOURCES") rtl/test/qwen_split/tb_mu_context_real_link.sv rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu.svh > "$OUT/source.sha256"
for spec in "${@:-0}"; do
 name=mut$spec; flags="-GMUT=$spec"; [ "$spec" != full ] || { name=full; flags='-GFULL=1'; }
 mkdir -p "$OUT/$name"
 "$VL" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH \
  -DOT_MEM_NO_INIT -Irtl/qwen_sys/d2d_static_20261015 --top-module tb_mu_context_real_link $flags --Mdir "$OUT/$name/obj" \
  -f "$SOURCES" rtl/test/qwen_split/tb_mu_context_real_link.sv > "$OUT/$name/build.log" 2>&1 || { tail -25 "$OUT/$name/build.log"; exit 1; }
 /usr/bin/time -v "$OUT/$name/obj/Vtb_mu_context_real_link" > "$OUT/$name/run.log" 2> "$OUT/$name/run.time"
 if [ "$spec" = 0 ]; then grep '^MUCTX_REAL_LINK_PASS' "$OUT/$name/run.log";
 elif [ "$spec" = full ]; then grep '^MUCTX_FULL_STREAM_DIAGNOSTIC_NATIVE_FAULT' "$OUT/$name/run.log";
 else grep '^MUCTX_REAL_LINK_FAIL' "$OUT/$name/run.log"; fi
 done
