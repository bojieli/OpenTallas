#!/bin/bash
set -eu
OUT=$(realpath -m "$1"); R=$(cd "$(dirname "$0")/../../.." && pwd);mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version > "$OUT/verilator.txt";grep -q 5.050 "$OUT/verilator.txt"
S=rtl/qwen_sys/mu_embedding_20261019/qfd_mu_embedding_cold_epoch_model.sv
BASE=rtl/test/qwen_split/fixtures/qfd_mu_embedding_epoch_d53159bb5.sv
buildrun(){
 local nu=$1 tag=$2 src=$3
 "$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_mu_cold_epoch_model -GNU="$nu" --Mdir "$OUT/obj$tag" "$src" "$R/$BASE" "$R/rtl/test/qwen_split/tb_mu_cold_epoch_model.sv" > "$OUT/build$tag.log" 2>&1
 set +e;"$OUT/obj$tag/Vtb_mu_cold_epoch_model" > "$OUT/run$tag.log" 2>&1;rc=$?;set -e
 cat "$OUT/run$tag.log"
 if [[ $tag == pos* ]];then test "$rc" = 0;grep -q COLD_MODEL_PASS "$OUT/run$tag.log";else test "$rc" != 0;grep -q COLD_MODEL_FAIL "$OUT/run$tag.log";fi
}
buildrun 1 pos1 "$R/$S"
buildrun 4 pos4 "$R/$S"
python3 - "$R/$S" "$OUT" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text();out=Path(sys.argv[2])
mutations={1:('init_token==resident_token&&','1\'b1&&'),2:('resident_epoch<=pending[0];','resident_epoch<=active[0];'),3:('reserved_pending ||','1\'b0 ||'),4:('if(COLD_PENDING&&(epoch_abort||new_epoch))','if(1\'b0)'),5:('assign expected_epoch=resident_epoch;','assign expected_epoch=COLD_PENDING?pending[resident_user]:resident_epoch;')}
for m,(a,b) in mutations.items():
 assert s.count(a)==1,(m,a,s.count(a))
 (out/f'mut{m}.sv').write_text(s.replace(a,b))
PY
for m in 1 2 3 4 5;do buildrun 4 mut$m "$OUT/mut$m.sv";done
for p in base off on;do
 if [ "$p" = base ];then src="$BASE";top=qfd_mu_embedding_epoch_publication;params='-chparam ENABLE 1';else src="$S";top=qfd_mu_embedding_cold_epoch_model;mode=0;[ "$p" = on ]&&mode=1;params="-chparam ENABLE 1 -chparam COLD_PENDING $mode";fi
 yosys -Q -p "read_verilog -sv $R/$src; hierarchy -top $top $params; synth -top $top -flatten -noabc; write_json $OUT/$p.json; stat" > "$OUT/synth$p.log" 2>&1
done
python3 - "$OUT" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);c={}
for n in ['base','off','on']:
 j=json.loads((p/(n+'.json')).read_text());m=next(iter(j['modules'].values()));c[n]=sum('DFF' in x['type'] for x in m['cells'].values())
assert c['base']==c['off'],c
assert 40<=c['on']-c['base']<=43,c
(p/'census.json').write_text(json.dumps({'FF':c,'extra':c['on']-c['base'],'scope':'generic MODEL state only; no native physical cost'},indent=2)+'\n')
print('COLD_MODEL_CENSUS_PASS',c)
PY
