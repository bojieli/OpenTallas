"""Exact selected S6C group geometry. This never changes RTL/view identity.

The die words are already the flat kit's ports. Keep every realized bit shape
when measuring reach; a canonical face alone loses the along-face displacement.
"""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KITS = {'qkd_kvs_grp_s6c': 'qkd_kvs_grp_s6a',
        'qkd_kvs_grp_h_s6c': 'qkd_kvs_grp_h_s6a'}
_CACHE = {}
INSTANCES = {}
_WORLD = {}


def _key(it, port):
    return (it.master, it.name, it.x, it.y, it.w, it.h, it.orient, port.lstrip('*').split('[')[0])


def load(master):
    if master not in KITS:
        return None
    if master in _CACHE:
        return _CACHE[master]
    kit = ROOT / 'physical/ref_tile' / KITS[master]
    spec = json.loads((kit / 'spec.json').read_text())
    if spec['top'] != master:
        raise ValueError(f'S6C geometry: wrong selected top {spec["top"]} for {master}')
    lef = kit / 'views' / master / f'{master}.lef'
    text = lef.read_text()
    w, h = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', text).groups())
    ports = {}
    for pm in re.finditer(r'\n\s*PIN\s+(\S+)(.*?)\n\s*END\s+\1(?=\s)', text, re.S):
        name = re.sub(r'\[\d+\]$', '', pm[1])
        if name in ('VDD', 'VSS'):
            continue
        rect = re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', pm[2])
        if not rect:
            raise ValueError(f'S6C geometry: missing pin shape {master}.{pm[1]}')
        x0, y0, x1, y1 = map(float, rect.groups())
        ports.setdefault(name, []).append(((x0+x1)/2, (y0+y1)/2))
    declared = {p: face for face, ps in spec['pins'].items() for p in ps}
    for name, points in ports.items():
        faces = Counter(min((('W', x), ('E', w-x), ('S', y), ('N', h-y)), key=lambda q: q[1])[0]
                        for x, y in points)
        if set(faces) != {declared.get(name)}:
            raise ValueError(f'S6C geometry: actual/declared face mismatch {master}.{name}: {faces}')
    rec = dict(w=w, h=h, ports=ports, faces=declared, orders=spec['pins'],
               lef=str(lef.relative_to(ROOT)), sha256=hashlib.sha256(lef.read_bytes()).hexdigest())
    _CACHE[master] = rec
    return rec


def points(it, port):
    rec = load(it.master)
    if rec is None:
        return None
    if abs(it.w + .024 - rec['w']) > .001 or abs(it.h + .024 - rec['h']) > .001:
        raise ValueError(f'S6C geometry: frame differs from exact view {it.name}: {it.w}x{it.h}')
    name = port.lstrip('*').split('[')[0]
    if name not in rec['ports']:
        raise ValueError(f'S6C geometry: port absent from actual view {it.master}.{name}')
    INSTANCES[it.name] = it
    key = _key(it, port)
    if key in _WORLD:
        return _WORLD[key]['points']
    pts = [(it.x + (rec['w']-x if it.orient in ('MY', 'R180') else x),
             it.y + (rec['h']-y if it.orient in ('MX', 'R180') else y))
            for x, y in rec['ports'][name]]
    _WORLD[key] = dict(points=pts, anchor=(sum(x for x, _ in pts)/len(pts), sum(y for _, y in pts)/len(pts)),
                      min_sum=min(x+y for x,y in pts), max_sum=max(x+y for x,y in pts),
                      min_diff=min(x-y for x,y in pts), max_diff=max(x-y for x,y in pts))
    return pts


def xy(it, port):
    pts = points(it, port)
    return None if pts is None else _WORLD[_key(it, port)]['anchor']


def far(inst, port, point):
    if inst not in INSTANCES:
        return None
    it = INSTANCES[inst]
    points(it, port)
    v = _WORLD[_key(it, port)]
    px, py = point
    return max(px+py-v['min_sum'], px-py-v['min_diff'],
               -px+py+v['max_diff'], -px-py+v['max_sum'])
