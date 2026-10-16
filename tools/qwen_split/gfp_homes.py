"""Source-pinned whole-block placement overrides, applied before pins/relays.

Recovered from GLOBAL-FP-Q's interrupted optional placement hook. Homes are a
candidate only. The complete pre-override graph fingerprint prevents a stale
logical graph or changed master from inheriting a placement receipt. Validation
is transactional: malformed or overlapping candidates leave the model intact.
"""
import hashlib
import json
import math
import os
from pathlib import Path

ORIENTS = ('R0', 'MX', 'MY', 'R180')
# one footprint; the generator assigns NK vs NL per tile AFTER homes (source-current identity wins on rebase)
TILE_PAIR = {'qfd_tile_nk', 'qfd_tile_nl'}


def source_fingerprint(model):
    insts = [dict(n=i.name, m=i.master, x=i.x, y=i.y, w=i.w, h=i.h,
                  o=i.orient) for i in model['insts']]
    buses = [dict(b=b, c=c, n=n, e=[list(x) for x in es])
             for b, c, n, es in model['buses']]
    root = Path(__file__).resolve().parents[2]
    generators = sorted(p for p in (root / 'tools/qwen_split').glob('*.py') if not p.name.startswith('test_'))
    generators += [root / ('tools/' + p) for p in
        ('qwen_rom_fulldie.py', 'qwen_rom_fulldie_b3r2.py', 'qwen_kv_die/tp8b_v5.py')]
    source_bytes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in generators}
    payload = dict(generator_sha256=source_bytes, die=model['die'], insts=sorted(insts, key=lambda i: i['n']),
                   buses=sorted(buses, key=lambda b: b['b']),
                   port_join=model.get('port_join', {}),
                   port_split=model.get('port_split', {}),
                   ties=model.get('ties', []),
                   master_params=model.get('master_params', {}),
                   source_bindings={k: model[k] for k in
                       ('native_control_contract', 'native_graph_bind', 'static_link_bind',
                        'res_train_bind', 'native_static_io_bind') if k in model})
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _rect(name, h):
    values = [float(h[k]) for k in ('x', 'y', 'w', 'h')]
    if not all(math.isfinite(x) for x in values) or min(values[2:]) <= 0:
        raise ValueError(f'OT_SPLIT_HOMES: {name} nonfinite/invalid rectangle')
    x, y, w, h = values
    return (x, y, x+w, y+h, name)


def _overlaps(rects, eps=1e-3):
    rs = sorted(rects)
    bad = []
    for a, (x0, y0, x1, y1, n) in enumerate(rs):
        for u0, v0, u1, v1, k in rs[a+1:]:
            if u0 >= x1-eps:
                break
            if v0 < y1-eps and v1 > y0+eps:
                bad.append((n, k))
    return bad


def apply(model, path):
    raw = Path(path).read_bytes()
    d = json.loads(raw)
    if d.get('schema') not in ('opentallas.qwen.globalfp-homes.v1', 'opentallas.qwen.globalfp-q-homes.1705.v1'):
        raise ValueError('OT_SPLIT_HOMES: unexpected schema')
    if isinstance(d.get('reserve'), list):
        # GLOBAL-FP-Q 1705 homes name their reserved channels (slab vertical channels) without rectangles: they are
        # the gaps the homes leave free, so there is nothing extra to reserve here; the names stay in the receipt
        d['reserve_names'] = d.pop('reserve')
    digest = source_fingerprint(model)
    homes = d.get('homes')
    if not isinstance(homes, dict) or not homes:
        raise ValueError('OT_SPLIT_HOMES: nonempty homes object required')
    by = {i.name: i for i in model['insts']}
    rebase = None
    if d.get('source_model_sha256') != digest:
        # OT_SPLIT_HOMES_REBASE=1 (Q-COMPUTE-DIE, coordinator-adopted fpq_s6 on a newer graph): the homes still apply
        # only if EVERY current instance has a home with its exact master and outline; homes of instances the current
        # graph no longer has are dropped and recorded. The overlap/outside checks below stay.
        if os.environ.get('OT_SPLIT_HOMES_REBASE') != '1':
            raise ValueError('OT_SPLIT_HOMES: stale or missing source_model_sha256')
        missing = sorted(set(by) - set(homes))
        if missing:
            raise ValueError(f'OT_SPLIT_HOMES rebase: {len(missing)} current instances without a home, e.g. {missing[:4]}')
        dropped = sorted(set(homes) - set(by))
        homes = {n: h for n, h in homes.items() if n in by}
        rebase = dict(homes_fingerprint=d.get('source_model_sha256'), current_fingerprint=digest, dropped=dropped)
    if len(by) != len(model['insts']) or set(homes)-set(by):
        raise ValueError('OT_SPLIT_HOMES: duplicate or unknown instance')
    proposed = {n: dict(x=i.x, y=i.y, w=i.w, h=i.h, o=i.orient) for n, i in by.items()}
    moved = []
    for n, h in homes.items():
        i = by[n]
        same = h['m'] == i.master or (rebase is not None and {h['m'], i.master} <= TILE_PAIR)
        if not same or any(abs(float(h[k])-getattr(i,k)) > 1e-3 for k in ('w','h')):
            raise ValueError(f'OT_SPLIT_HOMES: {n} master/outline mismatch')
        if h['o'] not in ORIENTS:
            raise ValueError(f'OT_SPLIT_HOMES: {n} unsupported orientation')
        _rect(n, h)
        proposed[n].update(x=float(h['x']), y=float(h['y']), o=h['o'])
        if (i.x, i.y, i.orient) != (float(h['x']), float(h['y']), h['o']):
            moved.append(n)
    rects = [_rect(n, h) for n, h in proposed.items()]
    reserve = d.get('reserve', {})
    if not isinstance(reserve, dict) or set(reserve) & set(by):
        raise ValueError('OT_SPLIT_HOMES: invalid reservation names')
    rects += [_rect('reserve:'+n, h) for n, h in reserve.items()]
    W, H = model['die']['w'], model['die']['h']
    outside = [n for x,y,u,v,n in rects if x < -1e-3 or y < -1e-3 or u > W+1e-3 or v > H+1e-3]
    overlap = _overlaps(rects)
    if outside or overlap:
        raise ValueError(f'OT_SPLIT_HOMES: outside={outside[:4]}, overlaps={overlap[:4]}')
    for n, h in proposed.items():
        by[n].x, by[n].y, by[n].orient = h['x'], h['y'], h['o']
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), source_model_sha256=digest,
                candidate=d.get('candidate'), moved=len(moved), moved_names=moved,
                reserve=reserve, reserve_names=d.get('reserve_names', []), rebase=rebase, qualified=False,
                open=['actual pins and legal orientations', 'relay allocation and cut capacity',
                      'clock/reset delivery', 'compiler fixed-cycle calendar', 'GRT/TT/FF/DRC'])
