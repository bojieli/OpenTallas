"""Opt-in, zero-edge matched word contacts for the three unclosed band parents.

This is a source geometry proposal, never an inherited physical view.  The
whole graph still needs allocation, actual PG/contact access, and route proof.
"""
import os

FLAG = 'OT_SPLIT_ALIGN_BAND_WORDS'
SHIFT_X = -21.6
FIRST = {'ty': 16.188, 'tw': 410.412}
CLOCK = 409.884


def enabled():
    value = os.environ.get(FLAG, '0')
    if value not in ('0', '1'):
        raise ValueError(f'{FLAG}: expected 0 or 1')
    return value == '1'


def apply_pins(masters):
    if not enabled():
        return
    q = masters.get('qfd_sp_band_lanes')
    if q is None or (q.w, q.h) != (881.28, 1131.84):
        raise ValueError('band word alignment: unexpected band frame')
    for port, first in FIRST.items():
        spec = q.ports.get(port)
        if spec is None or spec[:4] != ('face', 4096, 'N', 'M5') or spec[5] != 2:
            raise ValueError(f'band word alignment: source ABI changed at {port}')
        # Generic face emission rounds the FIRST contact to the M5 track grid.
        # Keeping n*step/2 (rather than (n-1)*step/2) matches that real emitter.
        q.ports[port] = ('face', 4096, 'N', 'M5', first + 4096*.096/2, 2)
    if q.ports['ck'][1] != 1:
        raise ValueError('band word alignment: expected one parent ck')
    # The clock occupies the 1.104um gap between the two 4096-bit groups.
    q.ports['ck'] = ('face', 1, 'N', 'M5', CLOCK, 1)


def apply_homes(model, reserve=None):
    if not enabled():
        return None
    if not os.environ.get('OT_SPLIT_HOMES'):
        raise ValueError('band word alignment requires explicit whole-graph homes')
    from qwen_split.gfp_homes import _overlaps
    by = {i.name: i for i in model['insts']}
    moved = []
    for band in range(3):
        a, b = by.get(f'sp_band_lanes_{band}'), by.get(f'sp_port_tiles_{band}')
        if a is None or b is None or a.master != 'qfd_sp_band_lanes' or b.master != f'qfd_port_tiles_{band}':
            raise ValueError('band word alignment: missing actual band/slab pair')
        if a.orient != b.orient or a.orient not in ('R0', 'MX') or abs(a.x-b.x-129.6) > 1e-6:
            raise ValueError('band word alignment: incompatible peer orientation/offset')
        gap = a.y-b.y-b.h if a.orient == 'MX' else b.y-a.y-a.h
        if abs(gap-43.2) > .025:
            raise ValueError('band word alignment: incompatible word-face separation')
        moved.append(a.name)
    proposed = [(i.x+(SHIFT_X if i.name in moved else 0), i.y,
                 i.x+i.w+(SHIFT_X if i.name in moved else 0), i.y+i.h, i.name)
                for i in model['insts']]
    for name, rect in (reserve or {}).items():
        proposed.append((rect['x'], rect['y'], rect['x']+rect['w'],
                         rect['y']+rect['h'], 'reserve:'+name))
    outside = [n for x,y,u,v,n in proposed if min(x,y) < 0 or u > model['die']['w'] or v > model['die']['h']]
    overlap = _overlaps(proposed)
    if outside or overlap:
        raise ValueError(f'band word alignment: outside={outside[:3]}, overlaps={overlap[:3]}')
    for name in moved:
        by[name].x = round(by[name].x+SHIFT_X, 6)
    return dict(qualified=False, instances=moved, shift_x_um=SHIFT_X,
                first_contact_um=FIRST, parent_clock_contact_um=CLOCK,
                cycles_added=0, area_added_um2=0,
                open=['all incident named-pin reach/cuts', 'actual PG/contact access',
                      'actual parent clock/native/route proof'])
