"""Compare cluster upper-PG pin geometry against the placed die's PG pins.

Every input is digest-bound. The placement is read from DEF, not accepted from
an audit verdict. Both net identity and transverse stripe rectangles must match.
"""
import gzip
import hashlib
import json
import re
from pathlib import Path


def validate(root, reference, spec, grant):
    root = Path(root).resolve()
    def source(ref):
        p = (root / ref.get('source', '')).resolve()
        if not p.is_relative_to(root) or not p.is_file() or not ref.get('sha256'):
            raise ValueError('PG phase input must be an existing digest-bound repository file')
        if hashlib.sha256(p.read_bytes()).hexdigest() != ref['sha256']:
            raise ValueError('PG phase input digest mismatch')
        return gzip.open(p, 'rt').read() if p.suffix == '.gz' else p.read_text()
    audit = json.loads(source(reference))
    if audit.get('schema') != 'opentallas.cluster-pg-phase.v1' or audit.get('master') != spec['name']:
        raise ValueError('PG phase audit schema/master mismatch')
    if audit.get('grant_sha256') != grant['sha256']:
        raise ValueError('PG phase audit grant mismatch')
    from child_lint import parse_lef, is_pg
    die = parse_lef(source(audit['die_pg_view']))
    child = parse_lef(source(audit['cluster_view']))
    if child['name'] != spec['top']:
        raise ValueError('PG phase cluster LEF does not match the actual master')
    defs = source(audit['die_def'])
    units = re.search(r'UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;', defs)
    if not units:
        raise ValueError('die DEF has no database units')
    inst = re.escape(audit['instance'])
    cell = re.escape(child['name'])
    placement = re.search(r'-\s+'+inst+r'\s+'+cell+r'\s+[^;]*?\+\s+(?:FIXED|PLACED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)\b', defs)
    if not placement or placement[3] != 'N':
        raise ValueError('PG phase needs the actual R0/N master placement in the die DEF')
    scale = float(units[1]); ox, oy = float(placement[1])/scale, float(placement[2])/scale
    w, h = child['W'], child['H']
    # Rectangles have layer,x0,y0,x1,y1. M8 is horizontal and M9 vertical.
    def stripes(view, layer, offset):
        out = []
        axis = 2 if layer == 'M8' else 1
        long_axis = 1 if layer == 'M8' else 2
        for net, pin in view['pins'].items():
            if not is_pg(net, pin): continue
            identity = net
            for r in pin['rects']:
                if r[0] != layer: continue
                rr = [r[0], r[1]+offset[0], r[2]+offset[1], r[3]+offset[0], r[4]+offset[1]]
                span = (ox, ox+w) if layer == 'M8' else (oy, oy+h)
                cross = (oy, oy+h) if layer == 'M8' else (ox, ox+w)
                if rr[axis+2] <= cross[0] or rr[axis] >= cross[1]: continue
                length = max(0, min(rr[long_axis+2],span[1])-max(rr[long_axis],span[0]))
                if length < .90*(span[1]-span[0]): continue
                out.append((identity, max(rr[axis],cross[0]), min(rr[axis+2],cross[1])))
        return sorted(set(out))
    counts = {}
    for layer in ('M8', 'M9'):
        expected, actual = stripes(die, layer, (0,0)), stripes(child, layer, (ox,oy))
        if not expected or not actual:
            raise ValueError(f'{layer} phase audit lacks full-span die/cluster PG pin stripes')
        remaining = list(actual)
        # One database unit accommodates source/export quantization, no phase margin.
        tol = 1/scale+1e-9
        for net, lo, hi in expected:
            match = next((i for i,(an,al,ah) in enumerate(remaining)
                          if an == net and abs(al-lo) <= tol and abs(ah-hi) <= tol), None)
            if match is None:
                raise ValueError(f'{layer} stripe net/phase mismatch at {lo:g}..{hi:g} ({net})')
            remaining.pop(match)
        if remaining:
            raise ValueError(f'{layer} cluster has PG stripes absent from the die grid')
        counts[layer] = len(actual)
    return dict(instance=audit['instance'], origin_um=[ox,oy], stripes=counts)
