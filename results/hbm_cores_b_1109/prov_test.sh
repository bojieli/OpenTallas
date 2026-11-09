#!/bin/bash
cd /
set -eu
D=/srv/opentallas-scratch2/claude/kv-types-6/pc_detail
SRC=/srv/opentallas-scratch2/claude/kw35/src_e2rd
test -d $SRC/tools/autopilot || SRC=/srv/opentallas-scratch2/claude/kw35/src_c303pus
test -d $SRC/tools/autopilot || { ls /srv/opentallas-scratch2/claude/kw35/ | head; exit 3; }
echo SRC=$SRC
P=/srv/opentallas-scratch2/claude/kv-types-5/ev/plan_kvr8/plan_c.json
O=$D/prov_test; rm -rf $O; mkdir -p $O/routed
for spec in "qkd_kvs_pcc:a0e9f5c3fe3e" "qkd_kvs_pcc_h_head_p:df3060246f1f" "qkd_kvs_pcf:388dc9658f5c" "qkd_kvs_pcf_h_head_p:1445a073fae9"; do
  m=${spec%%:*}
  mkdir -p $O/routed/$m/c0
  cp -a $D/$m/$m.lef $D/$m/${m}_tt.lib $D/$m/${m}_ff.lib $D/$m/gates.json $D/$m/provenance.json $O/routed/$m/c0/
  cp -a $D/$m/detail_view.lef $D/$m/detail_receipt.json $O/routed/$m/c0/
  python3 -I - "$O/routed/$m/c0/meta.json" "$m" <<'PY'
import json,sys
m=sys.argv[2]
json.dump({"host":"epyc4","dir":"/x","job":"COUNTED %s pc_detail test"%m,"counted":True,"detailed_lef":"detail_view.lef","detailed_receipt":"detail_receipt.json","detail_bloat_factor":0},open(sys.argv[1],'w'))
PY
done
python3 -I $SRC/tools/autopilot/prov_view.py make --plan $P --type kv3_pc__cl5a95b461 --out $O --src $SRC --routed $O/routed 2>&1 | tail -30 | cut -c1-400
