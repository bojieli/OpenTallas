#!/usr/bin/env python3
"""collect the attnret gap stage: ATTNRET_DIR/<cfg>/<0|ddwin|ddbase>/bench.out -> ATTNRET_DIR/result.json"""
import json, re, sys
from pathlib import Path
A = Path(sys.argv[1]); stg = sys.argv[2] if len(sys.argv) > 2 else 'stg'
cases, fails = {}, []
span = comp = None
for c in ('rel', 'pos'):
    for m in ('0', 'ddwin', 'ddbase'):
        p = A / c / m / 'bench.out'
        t = p.read_text() if p.exists() else ''
        v = re.search(r'DV_LOWER_VEC attn (PASS|FAIL)', t)
        sp = re.search(r'= (\d+) edges \(compiled (\d+)\)', t)
        v = v.group(1) if v else 'NOT RUN'
        cases[f'{c}/{m}'] = dict(verdict=v, span=int(sp.group(1)) if sp else None, compiled=int(sp.group(2)) if sp else None)
        want = 'PASS' if m == '0' else 'FAIL'
        if v != want:
            fails.append(f'{c}/{m}: {v} (want {want})')
        if m == '0' and sp:
            if span is None:
                span, comp = int(sp.group(1)), int(sp.group(2))
            elif (span, comp) != (int(sp.group(1)), int(sp.group(2))):
                fails.append(f'{c}: span differs between rel and pos')
if span is None or span != comp:
    fails.append(f'measured span {span} != compiled {comp}')
r = dict(stage='attnret', verdict='PASS' if not fails else 'FAIL', grade=f'same build/source grade as stage {stg}',
         measured_span_edges=span, compiled_span_edges=comp, cases=cases, failures=fails,
         source=f'dv_lower_vec_bench --mode attn on the {stg} objects + {stg} measured vec ages (rel, pos)',
         span_rule='first dr word at the dvs_W5 return pin -> last o_proj x word at E5 (QW-ATTNRET)')
(A / 'result.json').write_text(json.dumps(r, indent=1))
print(r['verdict'], span, comp, fails)
