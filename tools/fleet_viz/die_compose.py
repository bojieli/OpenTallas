#!/usr/bin/env python3
"""die_compose: the die composition manifest of the die-level routed viewer (EXPLORER-P1, Fable review EXPLORER-REVIEW-1).

    python3 -I die_compose.py [--die s81] [--out <state>/die_compose]

One small JSON per (die, plan sha) -> <out>/<die>/<plan sha>.json plus <out>/<die>/latest.json (a copy).  It pins the die plan
and the layout packs the viewer will draw:

  packs      node id -> {job, id, header, r0 (level-0 raster object hashes), die [x0 y0 x1 y1] DBU, dbu, bytes, shapes, state,
              level, cores: [{core, name, master, origin [x y] DBU, orient, bbox}]}     one entry per UNIQUE master (type or core
              pack), reused by every instance.  Coordinates stay pack-local (the viewer applies offset + orient in float64).
  instances  [{name, node, pack (node id or null), state, x, y, w, h, orient, ok}]   x,y,w,h in DBU (die plan bbox), orient in
              R0 MX MY R180 (the R90 family is refused: layers would swap direction)
  Orientation: world = origin + S * local, S = diag(sx, sy) of the orient, origin = the bbox corner the flip maps onto the bbox
  lower-left (OpenDB dbTransform convention, the same as the macro origins in the type packs).
"""
import argparse, json, os, pathlib, sys, time
import brotli

HERE = pathlib.Path(__file__).resolve().parent
STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
STORE = pathlib.Path(os.environ.get('LV_STORE', HERE / 'layout_store'))
INDEX = pathlib.Path(os.environ.get('DESIGN_INDEX', STATE / 'design_index.json'))
SCHEMA = 'opentallas.fleet_viz.die_compose.v1'
SIGN = {'R0': (1, 1), 'MX': (1, -1), 'MY': (-1, 1), 'R180': (-1, -1)}


def pack_info(node):
    """latest closure of a node from the static store -> small pack record, or None"""
    ix = STORE / 'elements' / node / 'index.json'
    if not ix.is_file(): return None
    i = json.loads(ix.read_text())
    m = json.loads((STORE / 'elements' / node / ('%s.json' % i['latest'])).read_text())
    ob = m['objects']; h = ob.get('header')
    if not h or (m.get('verify') or {}).get('verdict') not in (None, 'IDENTICAL'): return None
    H = json.loads(brotli.decompress((STORE / 'objects' / h[:2] / (h + '.br')).read_bytes()))
    if H.get('overview_only'): return None
    r0 = {k[4:]: v for k, v in ob.items() if k.startswith("r/0/")}
    return dict(job=m['job'], id=m['id'], header=h, r0=r0, die=H['die'], dbu=H['dbu'], bytes=m.get('bytes'), shapes=(m.get('verify') or {}).get('shapes'),
                macros=[dict(name=q['name'], master=q['master'], origin=q['origin'], orient=q['orient'], bbox=q['bbox']) for q in H.get('macros') or []],
                n_objects=len(ob))


def build(die, idx):
    nodes = idx['nodes']; d = nodes[die]; P = d['plan']
    packs, inst = {}, []
    cache = {}

    def pk(node):
        if node not in cache: cache[node] = pack_info(node)
        return cache[node]

    for name, tnode, x, y, w, h, o in P['partitions']:
        n = nodes.get(tnode) or {}
        st = (n.get('status') or {}).get('state', 'unknown')
        X, Y, W, H = (round(v * 1000) for v in (x, y, w, h))
        rec = dict(name=name, node=tnode, state=st, x=X, y=Y, w=W, h=H, orient=o, pack=None, ok=False)
        p = pk(tnode) if n.get('level') == 'type' else None
        if p is None: rec['why'] = 'no pack'
        elif o not in SIGN: rec['why'] = 'orient ' + o
        elif [p['die'][2] - p['die'][0], p['die'][3] - p['die'][1]] != [W, H] or p['die'][:2] != [0, 0]:
            rec['why'] = 'pack die %s != plan bbox %dx%d' % (p['die'], W, H)
        else:
            rec['pack'] = tnode; rec['ok'] = True
            if tnode not in packs:
                cores = []
                for q in p['macros']:
                    cn = '%s.c.%s' % (die, q['master'])
                    cp = pk(cn) if cn in nodes else None
                    ok = cp is not None and q['orient'] in SIGN and cp['die'][:2] == [0, 0]
                    cores.append(dict(core=cn if ok else None, name=q['name'], master=q['master'], origin=q['origin'], orient=q['orient'], bbox=q['bbox']))
                    if ok and cn not in packs:
                        packs[cn] = {k: v for k, v in cp.items() if k != 'macros'} | dict(level='core', state=nodes[cn]['status']['state'], cores=[])
                packs[tnode] = {k: v for k, v in p.items() if k != 'macros'} | dict(level='type', state=st, cores=cores)
        inst.append(rec)
    n_ok = sum(1 for r in inst if r['ok']); signed_ok = sum(1 for r in inst if r['ok'] and r['state'] == 'signed')
    summary = dict(partitions=len(inst), with_pack=n_ok, signed_with_pack=signed_ok, unique_packs=len(packs),
                   unique_type_packs=sum(1 for p in packs.values() if p['level'] == 'type'), core_packs=sum(1 for p in packs.values() if p['level'] == 'core'),
                   pack_bytes=sum(p['bytes'] or 0 for p in packs.values()),
                   signed_instances=sum(1 for r in inst if r['state'] == 'signed'))
    return dict(schema=SCHEMA, die=die, label=d.get('label'), outline=[round(v * 1000) for v in P['outline']], dbu=1000,
                plan=dict(path=P['path'], commit=P.get('commit'), date=P.get('date')),
                index_generated=idx.get('generated'), made=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), packs=packs, instances=inst, summary=summary)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die', default='s81'); ap.add_argument('--out', default=str(STATE / 'die_compose'))
    a = ap.parse_args()
    idx = json.loads(INDEX.read_text())
    for die in a.die.split(','):
        m = build(die, idx)
        sha = pathlib.Path(m['plan']['path']).name.replace('.json.gz', '').replace('.json', '')
        out = pathlib.Path(a.out) / die; out.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(m, separators=(',', ':'))
        for fn in (sha + '.json', 'latest.json'):
            tmp = out / (fn + '.tmp'); tmp.write_text(raw); os.replace(tmp, out / fn)
        print(die, json.dumps(m['summary']), '->', out / (sha + '.json'), len(raw), 'bytes')


if __name__ == '__main__':
    main()
