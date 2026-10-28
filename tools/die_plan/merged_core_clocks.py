"""Exact opt-in clock bit coverage for one physical core tap.

HBM-STREETS-3 (COORD 10-27 19:12 HBM-STREETS-2 ruling 1): a core without a native LEF+Liberty is PENDING-VIEW (never
PASS): its merged tap stays at the plan clock pins (pins_file) on the 12.3 common latency budget and is retapped when the
signed view arrives.  audit() checks every merged core tap on its own and never stops at the first core."""
import json
import math
import re
from pathlib import Path

import cores as C


class PendingView(ValueError):
    """The core has no native LEF+Liberty yet (PENDING-VIEW, never PASS)."""


def has_view(core):
    return bool(core.get('lef') and core.get('lib') and C.resolve(core['lef']).is_file()
                and C.resolve(core['lib']).is_file())


def plan_pins(P, tn, tap, inst):
    """Plan-side checks only (explicit distinct names, real pins_file geometry) -> (names, core, found pin rows)."""
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
    return names, core, found


def pins(P, tn, tap, inst):
    """Merged pin names checked against the native LEF+Liberty.  PendingView when the core has no native view,
    ValueError on any real mismatch."""
    names, core, found = plan_pins(P, tn, tap, inst)
    if not has_view(core):
        raise PendingView(f'{tn}/{inst}: PENDING-VIEW no native LEF+Liberty for {core.get("module", inst)}; '
                          f'tap stays at plan clock pins {names}')
    # A merged declaration is a complete clock set, never a guessed bus base.
    clocks = C.clock_pins(core)
    if set(clocks) != set(names):
        raise ValueError(f'{tn}/{inst}: merged clock set differs from actual LEF/lib clocks')
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


def pins_or_pending(P, tn, tap, inst, pending=None):
    """pins(); for a PENDING-VIEW core the plan clock pins (plan-side checks still enforced), recorded in `pending`."""
    try:
        return pins(P, tn, tap, inst)
    except PendingView as e:
        if pending is not None:
            pending.append(dict(type=tn, inst=inst, tap=tap.get('name'), msg=str(e)))
        return plan_pins(P, tn, tap, inst)[0]


def tap_inst(P, tn, tap):
    """hard_cores[] inst a core tap names (`<inst>` or `<inst>.<pin>`, longest match), else None."""
    nm = tap.get('name', '')
    for i in sorted((c['inst'] for c in P.types[tn].get('hard_cores', []) or []), key=len, reverse=True):
        if nm == i or nm.startswith(i + '.'):
            return i
    return None


def audit(P):
    """Every merged core tap of every type, each checked on its own (never stops at the first core):
    [dict(type, inst, module, tap, status PASS|PENDING-VIEW|FAIL, msg)]."""
    out = []
    for tn, t in P.types.items():
        for tap in (t.get('clock') or {}).get('taps', []) or []:
            if not tap.get('merged_clock_ports'):
                continue
            inst = tap_inst(P, tn, tap)
            core = next((c for c in t.get('hard_cores', []) or [] if c['inst'] == inst), {})
            row = dict(type=tn, inst=inst, module=core.get('module', inst), tap=tap.get('name'))
            try:
                if inst is None:
                    raise ValueError(f'{tn}: core tap {tap.get("name")} names no hard_cores[] inst')
                pins(P, tn, tap, inst)
                row.update(status='PASS', msg='')
            except PendingView as e:
                row.update(status='PENDING-VIEW', msg=str(e))
            except (ValueError, OSError, KeyError, StopIteration) as e:
                row.update(status='FAIL', msg=str(e))
            out.append(row)
    return out
