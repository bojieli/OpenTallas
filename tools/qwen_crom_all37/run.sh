#!/bin/bash
set -euo pipefail
python3 - <<'PYCHECK'
import json,hashlib,pathlib
R=pathlib.Path('.')
for name,h in json.loads((R/'source.json').read_text()).items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==h,name
v=json.loads((R/'vectors/manifest.json').read_text())
for name,h in v['vector_sha256'].items():assert hashlib.sha256((R/'vectors'/name).read_bytes()).hexdigest()==h,name
m=json.loads((R/'released_mask_manifest.json').read_text())
M=pathlib.Path('/srv/opentallas-scratch/codex/qwen-native-1103/crom_r3_leaf/r1/masks')
for name,h in m['masks_sha256'].items():assert hashlib.sha256((M/name).read_bytes()).hexdigest()==h,name
print('PASS frozen RTL, expected-only vectors and48releasedROMmasks')
PYCHECK
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in 0 1 2;do
 /usr/bin/time -v "$VL" --binary --timing -j 1 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_crom8_r3_all37 -GMUT=$m --Mdir obj$m -f sources.f >build$m.log 2>&1
 /usr/bin/time -v obj$m/Vtb_crom8_r3_all37 +OT_ROM_DIR=/srv/opentallas-scratch/codex/qwen-native-1103/crom_r3_leaf/r1/masks +V="$PWD/vectors" +N=15420 +NC=111 >run$m.log 2>&1
 if [ "$m" = 0 ];then grep '^PASS crom_r3_all37' run$m.log;else grep '^FAIL crom_r3_all37' run$m.log;grep -q '^MISMATCH' run$m.log;fi
 done
