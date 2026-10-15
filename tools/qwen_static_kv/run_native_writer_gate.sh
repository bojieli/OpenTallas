#!/usr/bin/env bash
# Full production writer oracle plus exact trimmed-face and omitted-field proof.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory}; mkdir -p "$out"
top=tb_qkd_kv_static_writer_native
sources=("$root/rtl/lib/ot_rst_relay.sv" "$root/rtl/physical/ot_qkd_kv_static_writer_native.sv" "$root/rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv" "$root/rtl/test/qwen_static_kv/$top.sv")
if [[ -n "${NATIVE_WRITER_STRICT_MUT:-}" ]];then
  # Production-judged mutant (closure-loop "expect fail" bench): the tb checks a MUT/BAD build exactly as a
  # production run, so the command exits non-zero when (and only when) the defect is observed.
  m=$NATIVE_WRITER_STRICT_MUT; b=${NATIVE_WRITER_STRICT_BAD:-0}
  iverilog -g2012 -s "$top" -P"$top.MUT=$m" -P"$top.BAD=$b" -P"$top.STRICT=1" -o "$out/strict.sim" "${sources[@]}" > "$out/strict.compile.log" 2>&1
  vvp "$out/strict.sim" 2>&1 | tee "$out/strict.log"; rc=${PIPESTATUS[0]}
  grep -q '^PASS all36stages' "$out/strict.log" && exit 0
  grep -q 'FAIL' "$out/strict.log" || exit 0
  exit 1
fi
for mut in ${NATIVE_WRITER_MUTANTS:-0 1 2 3 4 5 6}; do
  iverilog -g2012 -s "$top" -P"$top.MUT=$mut" -o "$out/$mut.sim" "${sources[@]}" > "$out/$mut.compile.log" 2>&1
  if vvp "$out/$mut.sim" > "$out/$mut.log" 2>&1;then rc=0;else rc=$?;fi
  echo "$rc" > "$out/$mut.exit"
  if [[ "$mut" == 0 ]];then [[ "$rc" == 0 ]];grep -q '^PASS all36stages/all8192positions' "$out/$mut.log"
  elif [[ "$mut" == 3 ]];then [[ "$rc" != 0 ]];grep -q 'omitted semantic field mismatch' "$out/$mut.log"
  else [[ "$rc" == 0 ]];grep -q '^OBSERVED_FAIL' "$out/$mut.log";fi
  cat "$out/$mut.log"
done
sha256sum "${sources[@]}" > "$out/source.sha256"
