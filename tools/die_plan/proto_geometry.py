"""Post-placement per-bit feedthrough geometry for prototype collection."""
from pathlib import Path
from collections import Counter
import re
import math

# Legacy insts.tsv has only lower-left coordinates. This is the measured SIZE
# of the one station primitive used by g2.py in the pinned asap7lock SC LEF:
# asap7sc7p5t_28_R_1x_220121a.lef, DFFHQNx1_ASAP7_75t_R SIZE1.08 BY0.27.
# New dumps carry their actual bounding boxes and need no primitive lookup.
LEGACY_STATION_SIZE_UM = {'DFFHQNx1_ASAP7_75t_R': (1.08, .27)}
NUM = r'[-+\d.eE]+'


def hop_stats(src, reach=405.0):
    """Use actual post-DPL station cell centres, with fixed generated IO pins.

    probe.tcl identifies the expected station names/stages only. Its placement
    targets are never substituted for physical locations. Missing actual dumps,
    cells or cell dimensions are unqualified, even if routing overflow is zero.
    """
    src = Path(src)
    if not (src/'probe.tcl').exists():
        return dict(actual_sites=False, errors=['expected station inventory probe.tcl is missing'],
                    max_hop_um=None, over_reach={}, st_in_core=0)
    expected = {}
    text = (src/'probe.tcl').read_text()
    for m in re.finditer(r'place_inst -name st_(.+?)_(\d+)_(\d+) -location', text):
        expected[f'st_{m.group(1)}_{m.group(2)}_{m.group(3)}'] = (m.group(1), int(m.group(2)), int(m.group(3)))
    base = dict(slots=len({v[0] for v in expected.values()}), max_hop_um=None, over_reach={},
                over_reach_bits=0, st_in_core=0, st_in_core_slots={}, actual_sites=False, errors=[])
    if not expected:
        return dict(base, max_hop_um=0.0, actual_sites=True)
    if not (src/'io.tcl').exists() or not (src/'insts.tsv').exists():
        base['errors'] = ['actual station geometry requires io.tcl and post-placement insts.tsv']
        return base
    pins = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(
        rf'place_pin -pin_name \{{(\S+)\}} -layer \S+ -location \{{({NUM}) ({NUM})\}}',
        (src/'io.tcl').read_text())}
    actual, errors = {}, []
    for line in (src/'insts.tsv').read_text().splitlines():
        p = line.split('\t')
        if not p or p[0] not in expected:
            continue
        try:
            x, y = float(p[2]), float(p[3])
            if len(p) >= 6:
                x1, y1 = float(p[4]), float(p[5])
            else:
                w, h = LEGACY_STATION_SIZE_UM[p[1]]
                x1, y1 = x+w, y+h
            if not all(math.isfinite(v) for v in (x,y,x1,y1)) or x1 <= x or y1 <= y:
                raise ValueError('nonpositive actual cell bounding box')
            actual[p[0]] = (x, y, x1, y1)
        except (ValueError, IndexError, KeyError) as exc:
            errors.append(f'{p[0]}: missing/invalid actual cell geometry ({exc})')
    missing = sorted(set(expected)-set(actual))
    if missing:
        errors.append(f'{len(missing)} expected station cells absent from actual dump: '+', '.join(missing[:5]))
    if errors:
        return dict(base, errors=errors, missing_actual_cells=len(missing))
    blocks = [tuple(map(float, m.groups())) for m in re.finditer(
        rf'create_blockage -region \{{({NUM}) ({NUM}) ({NUM}) ({NUM})\}}', text)]
    chains = {}
    in_core = Counter()
    for name, (slot, bit, stage) in expected.items():
        x, y, x1, y1 = actual[name]
        chains.setdefault((slot, bit), {})[stage] = ((x+x1)/2, (y+y1)/2)
        if any(min(x1,c)-max(x,a)>1e-6 and min(y1,d)-max(y,b)>1e-6 for a,b,c,d in blocks):
            in_core[slot] += 1
    out = {}
    over_bits = 0
    for (slot, bit), chain in chains.items():
        pts = []
        if f'{slot}_i[{bit}]' in pins:
            pts.append(pins[f'{slot}_i[{bit}]'])
        pts += [chain[j] for j in sorted(chain)]
        if f'{slot}_o[{bit}]' in pins:
            pts.append(pins[f'{slot}_o[{bit}]'])
        hop = max((abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(pts,pts[1:])), default=0.)
        record = out.setdefault(slot, dict(max_hop_um=0., bits=0, stations=len(chain)))
        record['max_hop_um'] = max(record['max_hop_um'], hop)
        record['bits'] += 1
        over_bits += hop > reach+1e-6
    over = {k:v['max_hop_um'] for k,v in out.items() if v['max_hop_um']>reach+1e-6}
    return dict(base, actual_sites=True, max_hop_um=round(max(v['max_hop_um'] for v in out.values()), 4),
                over_reach={k:round(v,4) for k,v in sorted(over.items(),key=lambda kv:-kv[1])},
                over_reach_bits=over_bits, st_in_core=sum(in_core.values()),
                st_in_core_slots=dict(in_core.most_common(5)), station_cells=len(actual),
                coordinate_basis='actual post-placement cell centres; fixed generated IO pins')
