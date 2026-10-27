"""Exact opt-in clock bit coverage for one physical core tap."""
import json
import math
import re
from pathlib import Path

import cores as C


def pins(P, tn, tap, inst):
    names = tap.get('merged_clock_ports')
    if not isinstance(names, list) or len(names) < 2 or len(set(names)) != len(names):
        raise ValueError(f'{tn}/{inst}: distinct explicit merged clock pins required')
    core = next(c for c in P.types[tn]['hard_cores'] if c['inst'] == inst)
    if not P.path or not core.get('pins_file'):
        raise ValueError(f'{tn}/{inst}: actual clock pin geometry required')
    path = Path(core['pins_file'])
    if not path.is_absolute():
        path = Path(P.path).parent / path
    rows = json.loads(path.read_text())
    found = {p['name']: p for p in rows if p.get('name') in names}
    if set(found) != set(names) or sum(p.get('name') in names for p in rows) != len(names):
        raise ValueError(f'{tn}/{inst}: missing/duplicate actual merged clock pin')
    if any(not p.get('layer') or not all(isinstance(p.get(k), (int, float)) and math.isfinite(p[k])
                                       for k in ('x', 'y')) for p in found.values()):
        raise ValueError(f'{tn}/{inst}: finite physical clock pin coordinates required')
    if len({(p['layer'], p['x'], p['y']) for p in found.values()}) != len(names):
        raise ValueError(f'{tn}/{inst}: merged clock pins must keep distinct physical windows')
    # A merged declaration is a complete clock set, never a guessed bus base.
    clocks = C.clock_pins(core)
    if set(clocks) != set(names):
        raise ValueError(f'{tn}/{inst}: merged clock set differs from actual LEF/lib clocks')
    if not core.get('lef') or not core.get('lib'):
        raise ValueError(f'{tn}/{inst}: selected native LEF and Liberty required')
    lef_text = C.resolve(core['lef']).read_text()
    lib_clocks = C.lib_clocks(C.resolve(core['lib']))
    if set(lib_clocks) != set(names):
        raise ValueError(f'{tn}/{inst}: actual Liberty clock coverage differs')
    for name in names:
        match = re.search(r'(?m)^\s*PIN\s+' + re.escape(name) +
                          r'\s*$(.*?)^\s*END\s+' + re.escape(name) + r'\s*$', lef_text, re.S | re.M)
        body = match.group(1) if match else ''
        rect = re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', body)
        if not re.search(r'DIRECTION\s+INPUT\s*;', body) or not re.search(r'USE\s+CLOCK\s*;', body) or not rect:
            raise ValueError(f'{tn}/{inst}/{name}: actual LEF input clock required')
        x0, y0, x1, y1 = map(float, rect.groups())
        point = found[name]
        if abs((x0+x1)/2-point['x']) > .001 or abs((y0+y1)/2-point['y']) > .001 or not re.search(r'LAYER\s+'+re.escape(point['layer'])+r'\s*;',body):
            raise ValueError(f'{tn}/{inst}/{name}: LEF clock geometry differs from native pin map')
    return names
