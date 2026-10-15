#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out
python3 - <<'VERIFY'
import json,hashlib,pathlib
p=pathlib.Path('.');m=json.loads((p/'manifest.json').read_text())
for n,d in m['files'].items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==d['sha256'],n
print('PASS exact source manifest03c7c9158')
VERIFY
for m in 2 3 4 5 6; do
 iverilog -g2012 -s tb_qkd_kv_native_programme -Ptb_qkd_kv_native_programme.MUT=$m -Ptb_qkd_kv_native_programme.BAD=0 -o out/m$m.sim ot_rst_relay.sv qkd_kv_native_programme.sv qkd_kv_static_writer.sv ot_qkd_kv_static_writer_native.sv tb_qkd_kv_native_programme.sv >out/m$m.compile.log 2>&1
 vvp out/m$m.sim >out/m$m.log 2>&1
 grep -Eq "^PASS observed negative MUT$m BAD0 errors[1-9][0-9]* writer_fault[01]$" out/m$m.log
 cat out/m$m.log
done
iverilog -g2012 -s tb_qkd_kv_native_programme -Ptb_qkd_kv_native_programme.MUT=0 -Ptb_qkd_kv_native_programme.BAD=1 -o out/bad.sim ot_rst_relay.sv qkd_kv_native_programme.sv qkd_kv_static_writer.sv ot_qkd_kv_static_writer_native.sv tb_qkd_kv_native_programme.sv >out/bad.compile.log 2>&1
vvp out/bad.sim >out/bad.log 2>&1
grep -q '^PASS refused malformed ascending boot' out/bad.log
cat out/bad.log
