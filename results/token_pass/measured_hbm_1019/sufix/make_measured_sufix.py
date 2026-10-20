#!/usr/bin/env python3
"""HBM-SUFIX: --measured inputs for the recomposition = measured_rel.json (TOKSIM-HBM release row) with
  sufix_asbuilt : SU.VOP (ds_ar + qwen) replaced by units/su.json (prod_compile fixed, bound ot_hbm_su_static_top);
                  FUSED.ROW_NORM as-built (bound reducer lower bound, unchanged)
  sufix_pretree : + FUSED.ROW_NORM from results/rtl/toksim_hbm_su_1019/sfu/rownorm_fix/fragment.json (HH-6 pre-tree,
                  closed but NOT bound in GEN2e3 die.v; variant)
usage: make_measured_sufix.py OUTDIR"""
import json, sys, copy
from pathlib import Path
H = Path(__file__).resolve().parent.parent
R = H.parents[2]
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rel = json.loads((H / 'measured_rel.json').read_text())
su = json.loads((H / 'units/su.json').read_text())
a = copy.deepcopy(rel)
for des in ('ds_ar', 'qwen'):
    a['designs'][des]['SU.VOP'] = su['designs'][des]['SU.VOP']
a.setdefault('sources', {})['SU.VOP'] = 'units/su.json (HBM-SUFIX, claude/hbm-sufix-1019)'
(out / 'm_sufix_asbuilt.json').write_text(json.dumps(a, indent=1) + '\n')
b = copy.deepcopy(a)
fr = json.loads((R / 'results/rtl/toksim_hbm_su_1019/sfu/rownorm_fix/fragment.json').read_text())
rn = b['designs']['qwen']['FUSED.ROW_NORM']
for k, v in fr['shapes'].items():
    assert k in rn['shapes'], k
    rn['shapes'][k] = dict(rn['shapes'][k], **{x: v[x] for x in ('cycles', 'golden') }, notes='HH-6 pre-tree (not die-bound): ' + str(v.get('notes', ''))[:300])
rn['grade'] = fr['grade']
(out / 'm_sufix_pretree.json').write_text(json.dumps(b, indent=1) + '\n')
print('wrote', out)
