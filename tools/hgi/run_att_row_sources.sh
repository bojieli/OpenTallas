#!/usr/bin/env bash
set -euo pipefail
src=${1:?source root}
out=${2:?output directory}
mkdir -p "$out"
rtl="$src/rtl/hbm_accel/generic/g12/ot_hgi_att_row_sources.sv"
tb="$src/rtl/test/hgi/tb_hgi_att_row_sources.sv"
for mode in golden ring-zero drop-c c-order; do
  params=()
  case "$mode" in
    ring-zero) params=(-Ptb_hgi_att_row_sources.MUT_RING_ZERO=1);;
    drop-c) params=(-Ptb_hgi_att_row_sources.MUT_DROP_C=1);;
    c-order) params=(-Ptb_hgi_att_row_sources.MUT_C_REVERSE=1);;
  esac
  iverilog -g2012 -s tb_hgi_att_row_sources "${params[@]}" -o "$out/$mode.vvp" "$rtl" "$tb" >"$out/$mode.build.log" 2>&1
  set +e
  vvp "$out/$mode.vvp" >"$out/$mode.log" 2>&1
  rc=$?
  set -e
  echo "$rc" >"$out/$mode.rc"
  if [[ "$mode" == golden ]]; then test "$rc" -eq 0; rg 'PASS CF-ATT' "$out/$mode.log";
  else test "$rc" -ne 0; rg 'FATAL' "$out/$mode.log"; fi
done
sha256sum "$rtl" "$tb" >"$out/source.sha256"
