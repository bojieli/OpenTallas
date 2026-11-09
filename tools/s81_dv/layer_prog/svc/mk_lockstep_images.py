"""S81-SVC-5 lock-step images: one fixture, H16 (1 job) and H8 (2 passes) + the H8 two-pass compiler mutants."""
import json, sys
from pathlib import Path
R = Path(sys.argv[1]); out = Path(sys.argv[2]); fx = sys.argv[3]
sys.path.insert(0, str(R / 'tools/s81_dv/layer_prog'))
import lower_svc as L
res = {}
for h, muts in ((16, (None,)), (8, (None, 'hb_swap', 'pass_drop', 'pass_swap', 'more_off'))):
    for m in muts:
        j, s = L.build(fx, allq=True, timing_profile='closing_allq', heads=h, mutant=m)
        rec = L.bench_image(j, s, out / f'h{h}' / (m or 'base'))
        res[f'h{h}/{m or "base"}'] = {k: rec.get(k) for k in ('go', 'pv_first', 'pv_last', 'done_w', 'done_e', 'so', 'allq', 'heads')}
        if h == 8:
            res[f'h{h}/{m or "base"}']['passes'] = rec['passes']
print(json.dumps(res, indent=1))
