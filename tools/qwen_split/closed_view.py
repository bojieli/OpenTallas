"""Q-NETLIST 2026-10-16: die frames from a master's hardened view (physical/ref_tile/<m>/views/<m>/<m>.lef).

The compute-die generator drew qfd_rstseq (54 x 54) and qfd_rstsync (54 x 32.4) as historical generated frames while
their hard leaves were closed at 21.6 x 21.6 (FILL-Q r3, tools/ref_tile/specs_qrst), so bind_real refused both views
('outline: case 53.976 x 53.976, view 21.6 x 21.6') and the die ran a generated frame instead of the real abstract.
The structural fix is to size the die slot from the view (the view is the physical truth; growing the leaf to the old
frame would re-open a closed element): view_frame() returns the view's outline and every signal pin (face, layer,
along-face coordinate) so the die master is drawn exactly as the abstract that bind_real swaps in.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PG = {'VDD', 'VSS'}


def view_lef(master):
    p = ROOT / f'physical/ref_tile/{master}/views/{master}/{master}.lef'
    return p if p.exists() else None


def view_frame(master):
    """(w, h, {pin: (face, layer, coordinate_um)}) of the hardened view, or None when the master has no view."""
    p = view_lef(master)
    if p is None:
        return None
    t = p.read_text()
    m = re.search(rf'MACRO {master}\b(.*?)END {master}\b', t, re.S)
    if not m:
        return None
    body = m.group(1)
    w, h = (float(x) for x in re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', body).groups())
    pins = {}
    for pm in re.finditer(r'PIN (\S+)(.*?)END \1\b', body, re.S):
        name, blk = pm.group(1), pm.group(2)
        if name in PG:
            continue
        lay = re.search(r'LAYER (\S+)', blk).group(1)
        x0, y0, x1, y1 = (float(v) for v in re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', blk).groups())
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        d = {'W': x0, 'E': w - x1, 'S': y0, 'N': h - y1}
        face = min(d, key=d.get)
        pins[name] = (face, lay, round(cy if face in 'WE' else cx, 4))
    return w, h, pins


def apply(q, frame):
    """redraw generated master q (tp8b Master) as the view frame: outline + every pin at the view's location"""
    w, h, pins = frame
    q.w, q.h = w, h
    for p in list(q.ports):
        if p not in pins:
            raise ValueError(f'{q.name}: die port {p} not a pin of the hardened view')
    q.ports, q.order = {}, []
    for p, (face, lay, z) in pins.items():
        q.ports[p] = ('pins', 1, face, lay, [z], 1)
        q.order.append(p)
    return q
