"""topo.py SCHED...: BF leaf return path latency per schedule (frame_return_plan.leaf_path)"""
import json, sys
import frame_return_plan as P
for f in sys.argv[1:]:
    s = json.load(open(f)); t = s['topology']
    leaves = sorted(k for k in json.dumps(t).split('"') if k.endswith('.r') and k[1:-3].isdigit() and k[-3] in 'we')
    out = {}
    for k in sorted(set(leaves)):
        try: out[k] = P.leaf_path(t, k)[0]
        except Exception as e: out[k] = repr(e)[:40]
    print(f.split('/')[-2], f.split('/')[-1][:22], {k: v for k, v in out.items() if k[1:-3] in ('4', '8', '13', '1', '5', '10')})
