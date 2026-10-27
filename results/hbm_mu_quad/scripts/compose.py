#!/usr/bin/env python3
"""HBM-MU-QUAD compose: planS2 bundle + unified quad hub types (NW/NE) + die growth +794.88 (hub row, root partition
straddle growth, rows above shifted) -> planU1.  Usage: compose.py TOOLS planS2_dir NW.json NE.json out_dir"""
import json, sys, shutil, hashlib, pathlib
tools, s2, nw, ne, out = sys.argv[1:6]
sys.path.insert(0, tools); import hbm_r11_delta as R11
out = pathlib.Path(out)
if out.exists(): raise SystemExit('exists')
shutil.copytree(s2, out, ignore=shutil.ignore_patterns('die_plan.json', 'die_plan.sha256'))
P = json.load(open(pathlib.Path(s2) / 'die_plan.json'))
H_old = P['partition_types']['q_hub_nw']['outline_um'][1]
for tn, f in (('q_hub_nw', nw), ('q_hub_ne', ne)):
    t = json.load(open(f)); old = P['partition_types'][tn]
    assert old['outline_um'][0] == t['outline_um'][0]
    P['partition_types'][tn] = t
H_new = P['partition_types']['q_hub_nw']['outline_um'][1]
rep = R11.grow_die(P, ['NW_hub', 'NE_hub'], H_old, H_new, grow_row=False)
s = json.dumps(P, indent=1) + '\n'
(out / 'die_plan.json').write_text(s)
(out / 'die_plan.sha256').write_text(hashlib.sha256(s.encode()).hexdigest() + '  die_plan.json\n')
(out / 'compose_report.json').write_text(json.dumps(dict(H_old=H_old, H_new=H_new, growth=rep), indent=1) + '\n')
d = P['die']['outline_um']
print(json.dumps(dict(sha=hashlib.sha256(s.encode()).hexdigest()[:8], die=d, area_mm2=round(d[0] * d[1] / 1e6, 3), dH=rep['dH_um'], ins=rep['insertion_y_um'], grown=rep['grown_types'], gaps=len(rep['hub_row_gap_rects_um']))))
