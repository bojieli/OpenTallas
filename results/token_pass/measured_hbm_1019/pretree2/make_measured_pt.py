#!/usr/bin/env python3
"""HBM-PRETREE2: --measured input = measured_rel.json with SU.VOP from units/su.json (reductions on the bound pre-tree)
and FUSED.ROW_NORM from the HH-6 pre-tree fragment (as HBM-SUFIX sufix_pretree).  usage: make_measured_pt.py OUT.json"""
import json, sys, copy
from pathlib import Path
H = Path(__file__).resolve().parent.parent
R = H.parents[2]
rel = json.loads((H / 'measured_rel.json').read_text())
su = json.loads((H / 'units/su.json').read_text())
a = copy.deepcopy(rel)
for des in ('ds_ar', 'qwen'):
    a['designs'][des]['SU.VOP'] = su['designs'][des]['SU.VOP']
a.setdefault('sources', {})['SU.VOP'] = 'units/su.json (HBM-PRETREE2: reductions through the bound HH-6 pre-tree)'
fr = json.loads((R / 'results/rtl/toksim_hbm_su_1019/sfu/rownorm_fix/fragment.json').read_text())
rn = a['designs']['qwen']['FUSED.ROW_NORM']
for k, v in fr['shapes'].items():
    rn['shapes'][k] = dict(rn['shapes'][k], **{x: v[x] for x in ('cycles', 'golden')}, notes='HH-6 pre-tree: ' + str(v.get('notes', ''))[:300])
rn['grade'] = fr['grade']
Path(sys.argv[1]).write_text(json.dumps(a, indent=1) + '\n')
print('wrote', sys.argv[1])
