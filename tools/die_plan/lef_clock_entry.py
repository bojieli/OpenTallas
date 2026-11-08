"""Opt-in clock entry against actual LEF rectangles. No blanket-OBS waiver.

Only a rectangular, zero-origin macro and an explicitly named real clock pin
are supported. Unsupported geometry raises; callers retain their solid box.
"""
import math
import re

_NUM = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'


def transform(rect, size, site):
    x, y, orient = site
    w, h = size
    f = {'R0': lambda a,b:(a,b), 'MY':lambda a,b:(w-a,b),
         'MX':lambda a,b:(a,h-b), 'R180':lambda a,b:(w-a,h-b)}.get(orient)
    if f is None:
        raise ValueError('unsupported clock-entry orientation: '+orient)
    a,b = f(*rect[:2]); c,d = f(*rect[2:])
    return (x+min(a,c), y+min(b,d), x+max(a,c), y+max(b,d))


def geometry(text, master, pin, top, site):
    """Return actual transformed upper OBS/other PIN boxes and target PIN boxes.

    Both upper-layer OBS sections must be explicit, including after an access
    window has been cut from a blanket. Empty/unknown views are never free space.
    Selected pin is retained separately and must exist below the entry layer.
    """
    m = re.search(r'^\s*MACRO\s+'+re.escape(master)+r'\s*$(.*?)^\s*END\s+'+re.escape(master)+r'\s*$', text, re.M|re.S)
    if not m:
        raise ValueError('missing exact LEF master '+master)
    body = m.group(1)
    sm = re.search(r'\bSIZE\s+('+_NUM+r')\s+BY\s+('+_NUM+r')\s*;', body)
    if not sm:
        raise ValueError('missing LEF SIZE')
    size = tuple(map(float,sm.groups()))
    origin = re.search(r'\bORIGIN\s+('+_NUM+r')\s+('+_NUM+r')\s*;',body)
    if origin and any(float(v) != 0 for v in origin.groups()):
        raise ValueError('nonzero LEF origin unsupported')
    if not all(math.isfinite(v) and v>0 for v in size):
        raise ValueError('invalid LEF SIZE')
    blocks, target, obs_layers = [], [], set()
    mode = layer = None
    for raw in body.splitlines():
        line = raw.split('#',1)[0].strip()
        if not line:
            continue
        if line.startswith('PIN '):
            mode = line.split()[1]; layer = None
        elif line == 'OBS':
            mode = 'OBS'; layer = None
        elif line.startswith('END'):
            if line == 'END' and mode != 'OBS':  # PORT end; PIN end follows
                layer = None
            else:
                mode = layer = None
        elif mode and line.startswith('LAYER '):
            lm = re.fullmatch(r'LAYER\s+M(\d+)\s*;',line)
            layer = int(lm.group(1)) if lm else (0 if re.fullmatch(r'LAYER\s+RVT[NP]\s*;',line) else None)
            if mode == 'OBS' and layer is not None:
                obs_layers.add(layer)
        elif mode and re.match(r'(RECT|POLYGON|PATH|VIA)\b',line):
            rm = re.fullmatch(r'RECT\s+('+_NUM+r')\s+('+_NUM+r')\s+('+_NUM+r')\s+('+_NUM+r')\s*;',line)
            if not rm or layer is None:
                raise ValueError('unsupported LEF geometry: '+line)
            rect = tuple(map(float,rm.groups()))
            if not all(math.isfinite(v) for v in rect) or rect[0]>=rect[2] or rect[1]>=rect[3]:
                raise ValueError('invalid LEF rectangle')
            mapped = transform(rect,size,site)
            if mode == pin:
                target.append((layer,mapped))
            elif layer in (top-1,top):
                blocks.append((layer, mapped))
    if not {top-1,top}.issubset(obs_layers):
        raise ValueError('upper OBS layers must be explicit')
    if not any(layer < top for layer,_ in target):
        raise ValueError('missing real lower-layer clock pin '+pin)
    return blocks,target,size


def overlap(a,b,eps=1e-6):
    return min(a[2],b[2])-max(a[0],b[0]) >= -eps and min(a[3],b[3])-max(a[1],b[1]) >= -eps


def entry_clear(footprints, blocks, target, top):
    """Check actual per-layer conductor footprints, never one layer's projection.

    Caller must supply emitted M5/M6/M7/via-enclosure footprints. This pure
    helper does not itself authorize a generated route or infer a missing via.
    """
    if set(footprints) != {top-2,top-1,top} or any(not boxes for boxes in footprints.values()):
        return False
    lower = footprints[top-2]
    real = all(any(layer == top-2 and r[0]-1e-6<=a[0] and r[1]-1e-6<=a[1]
                   and a[2]<=r[2]+1e-6 and a[3]<=r[3]+1e-6 for layer,r in target) for a in lower)
    connected = (all(any(overlap(a,b) for b in footprints[top-2]) and
                     any(overlap(a,c) for c in footprints[top]) for a in footprints[top-1])
                 and all(any(overlap(a,b) for b in footprints[top-1]) for a in footprints[top])
                 and all(any(overlap(a,b) for b in footprints[top-1]) for a in footprints[top-2]))
    return real and connected and not any(overlap(a,b) for layer,b in blocks for a in footprints.get(layer,()))


def validate_access(text, master, access, top, site, entry_box):
    """Fail-closed private opt-in, independently consumed by GEN and preflight.

    Footprints are proposed conductor/via enclosures, not a DRC waiver. Parent
    routing and actual post-route connectivity/DRC remain mandatory.
    """
    if set(access) != {'pin','footprints_um'}:
        raise ValueError('clock entry needs exactly pin and footprints_um')
    raw=access['footprints_um']
    if set(raw) != {f'M{top-2}',f'M{top-1}',f'M{top}'}:
        raise ValueError('clock entry needs all three consecutive metal footprints')
    footprints={}
    for layer,boxes in raw.items():
        if not isinstance(boxes,list) or not boxes:
            raise ValueError('missing conductor boxes')
        for r in boxes:
            if len(r)!=4 or not all(type(v) in (int,float) and math.isfinite(v) for v in r) or r[0]>=r[2] or r[1]>=r[3]:
                raise ValueError('invalid conductor box')
        footprints[int(layer[1:])]=boxes
    if len(footprints[top])!=1 or any(abs(a-b)>1e-6 for a,b in zip(footprints[top][0],entry_box)):
        raise ValueError('entry footprint differs from actual emitted utility pin')
    blocks,target,_=geometry(text,master,access['pin'],top,site)
    if not entry_clear(footprints,blocks,target,top):
        raise ValueError('clock entry conductor witness blocked or not on real pin')
    return True
