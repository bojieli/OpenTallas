"""M6 edge-contact permission; never a routing, power, or obstruction waiver."""
import hashlib
import json
import math
import re
from pathlib import Path

SCHEMA = 'opentallas.m6_pin_grant.v1'


def spec_digest(spec):
    return hashlib.sha256(json.dumps({k: v for k, v in spec.items() if k != 'm6_pin_grant'},
                                     sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate(grant, master):
    if not isinstance(grant, dict) or grant.get('schema') != SCHEMA or grant.get('master') != master:
        raise ValueError('M6 pin grant schema/master mismatch')
    for key in ('granted_by', 'reason'):
        if not isinstance(grant.get(key), str) or not grant[key].strip():
            raise ValueError(f'M6 pin grant requires {key}')
    for key, length in [('source_commit', 40), ('source_spec_sha256', 64)]:
        if not re.fullmatch('[0-9a-f]{' + str(length) + '}', str(grant.get(key, ''))):
            raise ValueError(f'M6 pin grant requires exact {key}')
    ports = grant.get('ports')
    if not isinstance(ports, list) or not ports:
        raise ValueError('M6 pin grant requires explicit named ports')
    if set(grant) - {'schema','master','granted_by','reason','source_commit','source_spec_sha256','ports'}:
        raise ValueError('M6 pin grant contains unknown fields')
    out = {}
    for p in ports:
        if not isinstance(p, dict) or set(p) != {'name','face','span_um','max_depth_um','max_area_um2'}:
            raise ValueError('M6 pin grant port fields do not match schema')
        name = p.get('name')
        if not isinstance(name, str) or not name or any(c in name for c in '*?') or name in out:
            raise ValueError('M6 pin grant needs unique exact port names, no wildcard')
        span = p.get('span_um', [])
        depth, area = p.get('max_depth_um'), p.get('max_area_um2')
        if p.get('face') not in ('N', 'S', 'E', 'W') or len(span) != 2 or not all(
                isinstance(x, (int, float)) and math.isfinite(x) for x in [*span, depth, area]):
            raise ValueError(f'M6 pin grant invalid contact bounds for {name}')
        if not 0 <= span[0] < span[1] or not 0 < depth <= 1 or not 0 < area <= 1:
            raise ValueError(f'M6 pin grant oversized/invalid edge contact for {name}')
        out[name] = p
    return out


def approved(name, rect, model, ports):
    p = ports.get(name)
    if not p or model['pins'][name]['use'] in ('POWER', 'GROUND') or name in ('VDD', 'VSS'):
        return False
    layer, x0, y0, x1, y1 = rect
    if layer != 'M6' or x1 <= x0 or y1 <= y0:
        return False
    w, h, d = model['W'], model['H'], p['max_depth_um']
    f = p['face']
    a, b = (y0, y1) if f in ('W', 'E') else (x0, x1)
    edge = {'W': x0 <= .001 and x1 <= d, 'E': x1 >= w - .001 and x0 >= w - d,
            'S': y0 <= .001 and y1 <= d, 'N': y1 >= h - .001 and y0 >= h - d}[f]
    return (edge and x0 >= -.001 and y0 >= -.001 and x1 <= w + .001 and y1 <= h + .001
            and a >= p['span_um'][0] - .001 and b <= p['span_um'][1] + .001
            and (x1-x0)*(y1-y0) <= p['max_area_um2'] + 1e-9)


def _section(text, name):
    m = re.search(r'(?ms)^\s*' + name + r'\s+(\d+)\s*;(.*?)^\s*END\s+' + name + r'\s*$', text)
    if not m:
        raise ValueError(f'routed DEF requires {name} section')
    entries = re.findall(r'(?ms)^\s*-\s+(\S+)\s+(.*?);', m[2])
    if len(entries) != int(m[1]):
        raise ValueError(f'routed DEF {name} entry count mismatch')
    return entries


def _metal(layer):
    m = re.fullmatch(r'M(\d+)', layer)
    return int(m[1]) if m else 0


def audit_def(path, model, ports, tech_lef=None):
    """Check raw routed DEF, independently of abstract OBS stripping or PORT rewriting.

    M6 via landing rectangles are allowed only inside that net's approved M6 BPin.
    Via definitions must be in DEF or the exact read-tech LEF; unresolved vias fail closed.
    """
    text = Path(path).read_text()
    um = re.search(r'UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;', text)
    design = re.search(r'(?m)^\s*DESIGN\s+(\S+)\s*;', text)
    if not um or not design or design[1] != model['name']:
        raise ValueError('routed DEF units/master mismatch')
    if re.search(r'\b(?:POLYGON|VIAITERATE)\b', text):
        raise ValueError('pin-only DEF audit requires explicit RECT and expanded via geometry')
    scale = int(um[1])
    fails, contacts, high_def = [], {}, {}
    def normalize(n):
        return n.replace('\\', '')
    def point(x, y, orient):
        return {'N': (x,y), 'S': (-x,-y), 'E': (y,-x), 'W': (-y,x),
                'FN': (-x,y), 'FS': (x,-y), 'FE': (y,x), 'FW': (-y,-x)}[orient]
    pg_nets = {normalize(n) for n,_ in _section(text, 'SPECIALNETS')}
    for name, body in _section(text, 'PINS'):
        name = normalize(name)
        net = re.search(r'\+\s+NET\s+(\S+)', body)
        if len(re.findall(r'\+\s+(?:PLACED|FIXED)\b', body)) > 1:
            fails.append(f'unexpanded multiple DEF PORT placements for {name}')
        place = re.search(r'\+\s+(?:PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*(\w+)', body)
        high = re.findall(r'\+\s+LAYER\s+(M\d+)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)', body)
        declarations = re.findall(r'\+\s+LAYER\s+(M\d+)\b', body)
        if len(declarations) != len(high):
            fails.append(f'unparsed DEF PORT geometry for {name}')
        for layer, a, b, c, d in high:
            if _metal(layer) <= 5:
                continue
            use = re.search(r'\+\s+USE\s+(\w+)', body)
            if (use and use[1] in ('POWER','GROUND')) or (net and normalize(net[1]) in pg_nets):
                fails.append(f'M6 pin {name} is PG in routed DEF')
                continue
            if not place or place[3] not in ('N','S','E','W','FN','FS','FE','FW') or name not in model['pins']:
                fails.append(f'unknown/unplaced above-M5 DEF pin {name}')
                continue
            points = [point(int(x), int(y), place[3]) for x,y in [(a,b),(a,d),(c,b),(c,d)]]
            r = (layer, (min(x for x,y in points)+int(place[1]))/scale,
                 (min(y for x,y in points)+int(place[2]))/scale,
                 (max(x for x,y in points)+int(place[1]))/scale,
                 (max(y for x,y in points)+int(place[2]))/scale)
            if not approved(name, r, model, ports):
                fails.append(f'ungranted DEF pin geometry {name}/{layer}')
            high_def.setdefault(name, []).append(r)
            if net:
                contacts.setdefault(normalize(net[1]), []).append(r)
    for name, pin in model['pins'].items():
        high_lef = [r for r in pin['rects'] if _metal(r[0]) > 5]
        actual = high_def.get(name, [])
        # Every LEF M6 shape must be exactly one real DEF PORT shape, and vice versa.
        def same(a,b):
            return a[0] == b[0] and all(abs(x-y) <= .001 for x,y in zip(a[1:],b[1:]))
        if any(not any(same(r,q) for q in actual) for r in high_lef) or any(
                not any(same(r,q) for q in high_lef) for r in actual):
            fails.append(f'LEF/DEF above-M5 PORT mismatch for {name}')
    blockage = re.search(r'(?ms)^\s*BLOCKAGES\s+\d+\s*;(.*?)^\s*END\s+BLOCKAGES', text)
    if blockage and any(_metal(l) > 5 for l in re.findall(r'\bLAYER\s+(M\d+)\b', blockage[1])):
        fails.append('raw DEF has above-M5 blockages/OBS')
    vias = {}
    widths = {}
    tech_sha = None
    if tech_lef:
        technology = Path(tech_lef).read_text()
        tech_sha = hashlib.sha256(technology.encode()).hexdigest()
        for layer, body in re.findall(r'(?ms)^\s*LAYER\s+(M\d+)\s*$(.*?)^\s*END\s+\1\s*$', technology):
            width = re.search(r'(?m)^\s*WIDTH\s+([0-9.]+)\s*;', body)
            if width:
                widths[layer] = float(width[1])
        for name, body in re.findall(r'(?ms)^\s*VIA\s+(\S+)(?:\s+(?i:DEFAULT))?\s*$(.*?)^\s*END\s+\1\s*$', technology):
            layer, rects = None, []
            for line in body.splitlines():
                lm = re.search(r'\bLAYER\s+(\S+)\s*;', line)
                if lm:
                    layer = lm[1]
                rm = re.search(r'\bRECT\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;', line)
                if rm and layer:
                    rects.append((layer,*map(float,rm.groups())))
            vias[name] = (rects or None) if not re.search(r"\b(?:POLYGON|PATH)\b", body) else None
    if re.search(r'(?m)^\s*VIAS\s+\d+', text):
        for name, body in _section(text, 'VIAS'):
            rects = re.findall(r'\+\s+RECT\s+(\S+)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)', body)
            if not rects:
                # A lower-only generated-rule via cannot touch above-cap metal. High ones need exact boxes.
                layers = re.search(r'\+\s+LAYERS\s+(\S+)\s+(\S+)\s+(\S+)', body)
                if layers and 0 < _metal(layers[1]) <= 5 and 0 < _metal(layers[3]) <= 5:
                    vias[name] = []
                else:
                    vias[name] = None
            else:
                vias[name] = [(l,*[int(x)/scale for x in (a,b,c,d)]) for l,a,b,c,d in rects]
    ndr_widths = {}
    if re.search(r'(?m)^\s*NONDEFAULTRULES\s+\d+', text):
        for rule, rule_body in _section(text, 'NONDEFAULTRULES'):
            ndr_widths[rule] = {layer: int(width)/scale for layer,width in
                re.findall(r'\+\s+LAYER\s+(M\d+)\s+WIDTH\s+(\d+)', rule_body)}
    for section in ('NETS', 'SPECIALNETS'):
        for name, body in _section(text, section):
            name = normalize(name)
            def contained(rect):
                # Exact wire rectangles, without the PORT-matching tolerance.
                return section == 'NETS' and any(p[0] == rect[0] and round(p[1]*scale) <= round(rect[1]*scale)
                    and round(p[2]*scale) <= round(rect[2]*scale) and round(p[3]*scale) >= round(rect[3]*scale)
                    and round(p[4]*scale) >= round(rect[4]*scale) for p in contacts.get(name, []))
            # Explicit SPECIALNET RECT geometry is never a terminal signal stub.
            for layer in re.findall(r'\+\s*RECT\s+(M\d+)\b', body):
                if _metal(layer) > 5:
                    fails.append(f'{section} {name}: nonpin routing geometry on {layer}')
            # Each NEW starts a new route path. Use the exact tech width and
            # DEF endpoint extensions, including the default half-width caps.
            for route_path in re.split(r'(?:\+\s*(?:ROUTED|FIXED|COVER)|\bNEW)\s+', body)[1:]:
                lm = re.match(r'(M\d+)\b(.*)', route_path, re.S)
                if not lm or _metal(lm[1]) <= 5:
                    continue
                layer, tail = lm.groups()
                rule = re.search(r'\+\s+NONDEFAULTRULE\s+(\S+)', body)
                width = ndr_widths.get(rule[1], {}).get(layer) if rule else widths.get(layer)
                wm = re.match(r'\s+(\d+)\s+(?=\()', tail)
                if wm:
                    width = int(wm[1])/scale
                if layer != 'M6' or section != 'NETS' or width is None or width <= 0:
                    fails.append(f'{section} {name}: unresolved/nonpin routing geometry on {layer}')
                    continue
                coords = []
                for pm in re.finditer(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+(-?\d+))?\s*\)', tail):
                    if not coords and '*' in (pm[1], pm[2]):
                        fails.append(f'{section} {name}: unresolved high route coordinate')
                        break
                    xy = tuple(coords[-1][i] if v == '*' else int(v)/scale for i,v in enumerate((pm[1],pm[2])))
                    coords.append((*xy, int(pm[3])/scale if pm[3] else width/2))
                if re.search(r'\b(?:RECT|MASK|STYLE|TAPER|TAPERRULE|SHAPE)\b', tail) or len(coords) < 2:
                    # A single point introduces a via, audited below; any other
                    # geometry syntax requires an exact decoder before acceptance.
                    if len(coords) != 1 or re.search(r'\b(?:RECT|MASK|STYLE|TAPER|TAPERRULE|SHAPE)\b', tail):
                        fails.append(f'{section} {name}: unparsed high route geometry')
                    continue
                for a,b in zip(coords, coords[1:]):
                    if a[0] == b[0]:
                        lo,hi = sorted((a,b), key=lambda p:p[1])
                        rect = (layer, a[0]-width/2, lo[1]-lo[2], a[0]+width/2, hi[1]+hi[2])
                    elif a[1] == b[1]:
                        lo,hi = sorted((a,b), key=lambda p:p[0])
                        rect = (layer, lo[0]-lo[2], a[1]-width/2, hi[0]+hi[2], a[1]+width/2)
                    else:
                        fails.append(f'{section} {name}: non-Manhattan high route')
                        continue
                    if not contained(rect):
                        fails.append(f'{section} {name}: {layer} wire outside granted PORT')
            # Via after a route coordinate. Lower wire layer does not prove a via stays below cap.
            route = re.split(r'\+\s*(?:ROUTED|FIXED|COVER)\s+', body)[1:]
            for path in route:
                if re.search(r"\bDO\s+\d+\s+BY\s+\d+", path):
                    fails.append(f"{section} {name}: unexpanded via array")
                last = None
                for match in re.finditer(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+[^)]*)?\)(?:\s+([A-Za-z_][\w./-]*))?', path):
                    if last is None and '*' in (match[1],match[2]):
                        fails.append(f'{section} {name}: unresolved route coordinate')
                        continue
                    xy = tuple((last[i] if v == '*' else int(v)/scale) for i,v in enumerate((match[1],match[2])))
                    last = xy
                    via = match[3]
                    if not via or via in ('NEW','+',';','(','RECT','MASK','STYLE','TAPER','TAPERRULE') or via.startswith('('):
                        continue
                    if via not in vias or vias[via] is None:
                        fails.append(f'{section} {name}: unresolved via {via}; expand DEF via geometry')
                        continue
                    om = re.match(r'\s+(FN|FS|FE|FW|N|S|E|W)\b', path[match.end():])
                    orient = om[1] if om else 'N'
                    for layer,a,b,c,d in vias[via]:
                        if _metal(layer) <= 5:
                            continue
                        points = [point(x,y,orient) for x,y in [(a,b),(a,d),(c,b),(c,d)]]
                        r = (layer,min(x for x,y in points)+xy[0],min(y for x,y in points)+xy[1],
                             max(x for x,y in points)+xy[0],max(y for x,y in points)+xy[1])
                        if layer != 'M6' or not contained(r):
                            fails.append(f'{section} {name}: above-M5 via {via} outside granted PORT')
    return fails, {'def_sha256': hashlib.sha256(text.encode()).hexdigest(), 'def': str(path),
                   'm6_def_ports': sorted(high_def), 'tech_lef_sha256': tech_sha}
