#!/usr/bin/env bash
set -euo pipefail
out=$1
mut=${2:-0}
python3 - <<'VERIFY'
import hashlib,json,pathlib
pkg=pathlib.Path('results/rtl/qwen_native_kv_programme_1103/leaf_package_v2')
m=json.loads((pkg/'manifest.json').read_text())
p=pathlib.Path('rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv')
assert hashlib.sha256(p.read_bytes()).hexdigest()==m['producer_sha256'],'canonical route RTL differs from frozen actual producer'
VERIFY
bash results/rtl/qwen_native_kv_programme_1103/leaf_package_v2/run.sh "$out" "$mut"
if [[ "$mut" == 1 ]];then
 grep -Eq '^PASS observed negative MUT1 BAD0 errors[1-9][0-9]* writer_fault1$' "$out/mut1.log"
 echo OBSERVED_FAIL_native_programme_MUT1
 exit 1
fi
