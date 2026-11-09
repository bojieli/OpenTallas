#!/bin/bash
cd /
set -eu
OUT=/srv/opentallas-scratch2/claude/kv-types-6/pc_detail
CX=/srv/opentallas-scratch2/claude/codex-kv-types-1113/pc_pg/views
SRC=/srv/opentallas-scratch2/claude/kw35/src_e2rd
test -d $SRC/tools/die_plan || SRC=/srv/opentallas-scratch2/claude/codex-kv-types-1113-src
mkdir -p $OUT
copy_view () { # module host dir
  m=$1; h=$2; d=$3
  mkdir -p $OUT/$m
  for f in $m.lef ${m}_tt.lib ${m}_ff.lib gates.json provenance.json pins.json $m.core.json; do
    cp -a $d/$f $OUT/$m/
  done
  python3 -I $SRC/tools/die_plan/abstract_detail.py splice --base $OUT/$m/$m.lef --detail $CX/$m/$m.lef --out $OUT/$m/detail_view.lef > $OUT/$m/receipt.tmp
  python3 -I - "$OUT/$m" <<'PY'
import json,sys,os
d=sys.argv[1]
r=json.load(open(d+'/receipt.tmp'))
r['bloat_factor']=0
r['bloat_source']='Codex exact export write_abstract_lef -bloat_factor 0 (codex/kv-types-safe-1113@f90cb5cb9e, native 6_final.odb)'
json.dump(r,open(d+'/detail_receipt.json','w'),indent=1)
os.remove(d+'/receipt.tmp')
print(os.path.basename(d),'check_ok',r['check_ok'],'pins_equal',r['detail_pins_equal_base'],'layers',r['layers_detailed'],'rects',r['rects'],'bytes',os.path.getsize(d+'/detail_view.lef'),'problems',r['problems'])
PY
}
copy_view qkd_kvs_pcc epyc2 $OUT/base/qkd_kvs_pcc
copy_view qkd_kvs_pcc_h_head_p epyc4 /srv/opentallas-scratch3/claude/kw32-views/qwen_kvsys/df3060246f1f/qkd_kvs_pcc_h_head_p
copy_view qkd_kvs_pcf epyc4 /srv/opentallas-scratch3/claude/kw32-views/qwen_kvsys/388dc9658f5c/qkd_kvs_pcf
copy_view qkd_kvs_pcf_h_head_p epyc2 $OUT/base/qkd_kvs_pcf_h_head_p
du -sh $OUT
