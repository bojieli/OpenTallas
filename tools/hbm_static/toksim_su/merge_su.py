#!/usr/bin/env python3
"""TOKSIM-HBM-su: merge the per-part fragments (suvop / hc / sfu) into units/su.json (brief schema).
Classes or shapes no fragment covers stay listed with cycles null, grade 'unmeasured'. Ratio = mean(measured/model) over the
measured shapes of a class (golden PASS or FAIL both kept; FAIL is graded measured-golden-FAIL). Also prints coverage."""
import json, sys, datetime
from pathlib import Path
CEN = Path('/home/ubuntu/wt/toksim-hbm-1019/results/token_pass/measured_hbm_1019/census_shapes.json')
FR = Path(__file__).resolve().parents[3] / 'results/rtl/toksim_hbm_su_1019'
OUT = Path('/home/ubuntu/wt/toksim-hbm-1019/results/token_pass/measured_hbm_1019/units/su.json')
MINE = {'ds_ar': ['SU.VOP', 'HC.HC_MIX', 'FUSED.HC_PRE_NORM', 'FUSED.HC_POST', 'FUSED.QDQ_FP8'],
        'qwen': ['SU.VOP', 'FUSED.ROW_NORM', 'SFU.GLU']}
branch = sys.argv[1] if len(sys.argv) > 1 else 'claude/toksim-hbm-su-1019'
cen = json.loads(CEN.read_text())
frags = {}
for p in sorted(FR.glob('*/fragment.json')):
    for des, cl in json.loads(p.read_text()).get('designs', {}).items():
        for c, v in cl.items():
            frags.setdefault(des, {})[c] = v
out = dict(group='su', branch=branch, updated_utc=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), designs={})
tot = cov = 0.0
for des, classes in MINE.items():
    D = out['designs'].setdefault(des, {})
    for c in classes:
        cc = cen[des]['classes'][c]
        f = frags.get(des, {}).get(c, {})
        shapes = {}
        rs = []; covc = 0.0
        for k, v in cc['shapes'].items():
            s = dict(f.get('shapes', {}).get(k) or {})
            if not s:
                s = dict(cycles=None, golden=None, notes='not measured by this lane')
            s['model_cost'] = v['model_cost']; s['n'] = v['n']
            if s.get('cycles') is not None:
                rs.append(s['cycles'] / v['model_cost']); covc += v['n'] * v['model_cost']
            shapes[k] = s
        unknown = set(f.get('shapes', {})) - set(cc['shapes'])
        assert not unknown, (des, c, 'shape keys not in census', list(unknown)[:2])
        e = {k: v for k, v in f.items() if k != 'shapes'}
        e['shapes'] = shapes
        if rs and 'ratio' not in e: e['ratio'] = sum(rs) / len(rs)
        e.setdefault('law', 'shape_table'); e.setdefault('grade', 'unmeasured' if not rs else 'measured-current-d4g')
        e.setdefault('pending', [])
        if any(s.get('golden') == 'FAIL' for s in shapes.values()) and e['grade'].startswith('measured'):
            e['grade'] = 'measured-golden-FAIL'
        e['coverage_model_sum'] = covc / cc['model_sum'] if cc['model_sum'] else 0
        D[c] = e
        tot += cc['model_sum']; cov += covc
        print(f"{des:6s} {c:18s} model_sum {cc['model_sum']:10.1f} covered {covc / cc['model_sum'] * 100:5.1f}% ratio {e.get('ratio')} grade {e['grade']}")
print(f'TOTAL covered {cov / tot * 100:.1f}% of {tot:.0f}')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=1) + '\n')
print('wrote', OUT)
