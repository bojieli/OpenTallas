#!/usr/bin/env bash
# Frozen all36 native writer fixture. Only standard Python, Icarus and vvp.
set -euo pipefail
pkg=$(cd "$(dirname "$0")" && pwd)
if [[ $# -lt 1 ]];then echo 'usage: run.sh FRESH_OUTPUT_DIR [0_or_1]' >&2;exit 2;fi
out=$1
mutants="0 1"
if [[ $# -ge 2 ]];then mutants=$2;fi
case "$mutants" in "0"|"1"|"0 1");; *) echo "only MUT0 production and scalar MUT1 are packaged" >&2; exit 2;; esac
python3 - "$pkg" <<'PY'
import hashlib,json,sys
from pathlib import Path
pkg=Path(sys.argv[1]);m=json.loads((pkg/'manifest.json').read_text())
for filename,item in m['files'].items():
    assert hashlib.sha256((pkg/filename).read_bytes()).hexdigest()==item['sha256'],filename+' differs from frozen source'
print('PASS frozen sources and external boot fixture SHA256')
PY
if [[ -e "$out" ]];then echo "output path must be fresh: $out" >&2;exit 2;fi
mkdir -p "$out"
out=$(cd "$out" && pwd)
cp "$pkg/boot.hex" "$out/boot.hex"
top=tb_qkd_kv_native_programme
for mut in $mutants;do
  iverilog -g2012 -s "$top" -P"$top.MUT=$mut" -P"$top.BAD=0" \
    -o "$out/mut$mut.sim" \
    "$pkg/ot_rst_relay.sv" "$pkg/qkd_kv_native_programme.sv" \
    "$pkg/qkd_kv_static_writer.sv" "$pkg/ot_qkd_kv_static_writer_native.sv" \
    "$pkg/tb_qkd_kv_native_programme.sv" > "$out/mut$mut.compile.log" 2>&1
  (cd "$out" && vvp "./mut$mut.sim") > "$out/mut$mut.log" 2>&1
  if [[ "$mut" == 0 ]];then
    grep -q '^PASS programme+native_writer all36 two_tokens .*cases1152 slots4608 sectors9216 ' "$out/mut$mut.log"
  else
    grep -q '^PASS observed negative MUT1 BAD0 errors[1-9][0-9]* writer_fault1$' "$out/mut$mut.log"
  fi
  cat "$out/mut$mut.log"
done
