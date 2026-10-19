#!/bin/bash
set -eu
OUT=$(realpath -m "$1");R=$(cd "$(dirname "$0")/../../.." && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"
"$V" --version > "$OUT/verilator.txt";grep -q 5.050 "$OUT/verilator.txt"
for m in 0 1 5 6 7 8 9;do
 "$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_sysface_accepted_identity -GMUT=$m --Mdir "$OUT/obj$m" "$R/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv" "$R/rtl/qwen_split/qfd_sys_face_accepted_mu_ctx.sv" "$R/rtl/qwen_split/qfd_sys_face_accepted_mu_identity.sv" "$R/rtl/test/qwen_split/tb_sysface_accepted_identity.sv" > "$OUT/build$m.log" 2>&1
 set +e
 "$OUT/obj$m/Vtb_sysface_accepted_identity" > "$OUT/run$m.log" 2>&1;rc=$?
 set -e
 cat "$OUT/run$m.log"
 if [ "$m" = 0 ];then test "$rc" = 0;grep -q ACCEPTIDENTITY_PASS "$OUT/run$m.log";else test "$rc" != 0;grep -q ACCEPTIDENTITY_FAIL "$OUT/run$m.log";fi
done
for p in old 0 1;do
 top=qfd_sys_face_accepted_mu_identity;args="-chparam EPOCH_EXPORT $p"
 if [ "$p" = old ];then top=qfd_sys_face_accepted_mu_ctx;args="";fi
 yosys -Q -p "read_verilog -sv $R/rtl/qwen_split/qfd_sys_face_accepted_mu_ctx.sv $R/rtl/qwen_split/qfd_sys_face_accepted_mu_identity.sv; hierarchy -top $top $args; synth -top $top -flatten -noabc; write_json $OUT/$p.json; stat" > "$OUT/synth$p.log" 2>&1
done
python3 - "$OUT" <<'PY'
from pathlib import Path
import json,sys,hashlib
p=Path(sys.argv[1]);counts={}
for n in ['old','0','1']:
 j=json.loads((p/f'{n}.json').read_text());m=next(iter(j['modules'].values()));counts[n]=sum(1 for c in m['cells'].values()if 'DFF' in c['type'])
assert counts['old']==counts['0'],counts
delta=counts['1']-counts['old'];assert 38<=delta<=42,counts
(p/'census.json').write_text(json.dumps(dict(FF=counts,extra_FF=delta,scope='generic source census only; no mapped physical area'),indent=2)+'\n')
print('ACCEPTIDENTITY_CENSUS_PASS',counts,f'extra{delta}/defaultoffzero')
PY
