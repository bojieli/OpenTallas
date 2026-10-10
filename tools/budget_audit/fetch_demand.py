"""Program-fetch demand per token / step under the simulator's ring rule (timing.schedule fetch_ready):
bytes fetched = image prefix + LOOP bodies larger than the ring re-fetched each iteration."""
import json, sys
from pathlib import Path
ROOT = Path('/home/ubuntu/OpenTallas'); sys.path.insert(0, str(ROOT / 'tools'))
from hgi_sim import timing as T, qwen_compiler as QC, dflash as D
from hgi_sim.records import rec_bytes, encode_program
ring = T.CAL['cp']['ring_bytes']['value']
def demand(recs, pos):
    ex = T.expand(recs, pos)
    offs, o = [], 0
    for r in recs: offs.append(o); o += rec_bytes(r)
    bodies = []
    for k, r in enumerate(recs):
        if r.unit == 'CTL' and r.op == 'LOOP':
            e = next(j for j in range(k + 1, len(recs)) if recs[j].unit == 'CTL' and recs[j].op == 'ENDLOOP')
            bodies.append((k, e, offs[e] - offs[k] + rec_bytes(recs[e])))
    fetched = 0; seen = set()
    for k, L, L1 in ex:
        inb = [b for b in bodies if b[0] < k <= b[1]]
        if inb and L > 0 and all(b[2] <= ring for b in inb): continue
        key = (k, L, L1)
        if key in seen: continue
        seen.add(key); fetched += rec_bytes(recs[k])
    return dict(records_in_image=len(recs), image_bytes=o, records_executed=len(ex), fetched_bytes=fetched,
                loop_bodies=[dict(lo=b[0], hi=b[1], bytes=b[2], fits_ring=b[2] <= ring) for b in bodies])
cfg = json.loads((ROOT / 'compiler/models/qwen3-8b/config.json').read_text())
md = QC.qwen_params(cfg); g = QC.Geometry(cfg, 8192)
out = {'ring_bytes': ring, 'qwen_P8191': demand(QC.program(g, md, cfg['num_hidden_layers']), 8191)}
try:
    from hgi_sim import dflash_timing as DT
    dcfg = json.loads(DT.DCFG.read_text())
    gd = D.DGeom(cfg, dcfg, 8192, 16)
    out['dflash_b16'] = demand(D.step_program(gd, md, timing_pos=8192-16), 8192-16)
    import inspect
    from hgi_sim import dflash_timing as DT
    src = inspect.getsource(DT)
    gd, mdd, pos = DT.setup(16) if hasattr(DT, 'setup') else (None, None, None)
except Exception as e:
    out['dflash_note'] = repr(e)
print(json.dumps({k:(dict(v, loop_bodies=v['loop_bodies']) if isinstance(v,dict) else v) for k,v in out.items()}))
