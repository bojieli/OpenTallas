#!/bin/bash
# H-D4G3b fork B: emit die.v from a contract and run the strict port bind (child closure on) as run_v16_d4b.sh does.
# Straps/pads files are derived from the contract itself (identity straps -> --strap-file; PAD straps -> --pad-file).
#   l2_bindcheck.sh CONTRACT.json OUTDIR      (run from the worktree root)
set -o pipefail
C=$1; O=$2; mkdir -p $O
python3 tools/hbm_die_v16/contract_die_v.py emit $C $O/die.v || { echo EMIT_FAIL; exit 2; }
python3 - $C $O <<'PY'
import json, sys, gzip
p, o = sys.argv[1], sys.argv[2]
c = json.load(gzip.open(p, 'rt') if p.endswith('.gz') else open(p))
ident, pads = set(), {}
for s in c['straps']:
    if str(s.get('reason', '')).startswith('PAD'):
        d = pads.setdefault(s['master'], dict(reason='DEDUPE spare input bits tied low (contract PAD straps)', ports={}))
        r = d['ports'].setdefault(s['port'], [])
        if [s['lo'], s['hi'] - 1] not in r:
            r.append([s['lo'], s['hi'] - 1])
    else:
        ident.add((s['master'], s['port']))
json.dump(dict(straps=sorted(ident)), open(o + '/straps.json', 'w'), indent=1)
json.dump(dict(pads=pads), open(o + '/die.v.pads.json', 'w'), indent=1)
PY
EXTRA=$(python3 -c "
import json,gzip,sys; p='$C'; c=json.load(gzip.open(p,'rt') if p.endswith('.gz') else open(p))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+i.get('rtl_deps',[])
      if not (f.startswith('rtl/') or '/rtl/' in f)})))")
python3 tools/die_port_bind.py $O/die.v $EXTRA --top hbm_v16_die --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb \
  --lib-root physical/asap7_memory_macros --lib-root physical/hbm_xp_aq_tree13_1014 ${L2_EXTRA_RTL:+$(for f in $L2_EXTRA_RTL/*.sv; do echo --rtl-file $f; done)} \
  --define OT_SMH_FC_HIER --strap-file $O/straps.json --pad-file $O/die.v.pads.json --out $O/port_bind.json > $O/port_bind.log 2>&1
rc=$?; tail -1 $O/port_bind.log; exit $rc
