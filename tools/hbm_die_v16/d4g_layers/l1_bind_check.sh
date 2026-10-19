#!/bin/bash
# H-D4G3b: emit die.v from a (layered) d4g contract and run the strict recursive port bind (as run_v16_d4b.sh).
#   l1_bind_check.sh CONTRACT.json OUTDIR      (run from the repo root)
set -o pipefail
C=$1; O=$2; mkdir -p $O
python3 tools/hbm_die_v16/contract_die_v.py emit $C $O/die.v || exit 3
cp results/arch/hbm_die_d4g/gen0/die.v.pads.json $O/die.v.pads.json
python3 -c "
import json,gzip,sys; p='$C'; c=json.load(gzip.open(p,'rt') if p.endswith('.gz') else open(p))
json.dump(dict(straps=sorted({(s['master'], s['port']) for s in c['straps']})), open('$O/straps.json','w'), indent=1)"
EXTRA=$(python3 -c "
import json,gzip; p='$C'; c=json.load(gzip.open(p,'rt') if p.endswith('.gz') else open(p))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+(i.get('rtl_deps') or [])
      if f.startswith('rtl/hbm_accel/die_glue/scoped_d4g/') or not (f.startswith('rtl/') or '/rtl/' in f)})))")
python3 tools/die_port_bind.py $O/die.v --top hbm_v16_die $EXTRA --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb \
  --rtl-root rtl --rtl-root physical/hbm_mtp/rtl --rtl-root physical/hbm_accel_die_views/common --rtl-root physical/hbm_accel_die_views/quant/rtl \
  --rtl-root physical/hbm_generic/argmax18/rtl --rtl-root physical/hbm_xp_aq_tree13_1014 --lib-root physical/asap7_memory_macros --lib-root physical/asap7_memory_macros_v2 \
  --define OT_SMH_FC_HIER --strap-file $O/straps.json --pad-file $O/die.v.pads.json --out $O/port_bind.json > $O/port_bind.log 2>&1; rc=$?
tail -1 $O/port_bind.log; exit $rc
