#!/bin/bash
set -eu
R=$PWD
E=$R/results/rtl/kv_ectl_h15_1020/ktree_audit
A=$R/../archives/ot_qkh_ktree_lk_nc32c-g1-1c272f08e
mkdir -p "$E"
python3 - "$A" <<'INNER'
from pathlib import Path
import sys,json,hashlib,subprocess
p=Path(sys.argv[1]);m=json.loads((p/'MIRROR_MANIFEST.json').read_text())
for n,h in m['copied_sha256'].items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h,(n,'mirror changed')
raw=p/'final/6_final.v'
if not raw.exists():
 with (p/'final/6_final.v.zst').open('rb') as f,raw.open('wb') as out:subprocess.run(['zstd','-dc'],stdin=f,stdout=out,check=True)
assert hashlib.sha256(raw.read_bytes()).hexdigest()==m['decompressed_expected_sha256']
print('KTREE_PRIVATE_MIRROR_SHA_PASS')
INNER
for mode in positive wrong_scale;do
 if [ "$mode" = positive ];then P='{"ADD_LAT":7,"MUL_LAT":6,"SCALE":1035273459,"MUT":0}';expect=pass
 else P='{"ADD_LAT":7,"MUL_LAT":6,"SCALE":1065353216,"MUT":0}';expect=fail;fi
 python3 tools/qwen_kv_die/kv_param_native_audit.py audit --root "$R" --module ot_qkh_ktree_lk_nc32c \
 --rtl rtl/hdc/nearhbm/ot_qkh_ktree_nc32c.sv --view physical/ref_tile/ot_qkh_ktree_lk_nc32c/views/ot_qkh_ktree_lk_nc32c \
 --params "$P" --archive-run "$A" --work "$E/work_$mode" --out "$E/$mode.audit.json" --expect "$expect" > "$E/$mode.client.log" 2>&1
 cat "$E/$mode.client.log"
done
