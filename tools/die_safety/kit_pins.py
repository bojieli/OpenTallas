#!/usr/bin/env python3
"""Stand-in fidelity (ROOT14 10-20): the die stand-in of a still-OPEN tile takes its pins from the tile kit's REAL pin
plan (face / order / layer), not from pins projected toward the neighbour centroid.

Why: S81 mu5k's 854k GRT overflow was one PHY-face funnel made by centroid-projected stand-in pins (19,904 bits, stand-in
max wire 631 um / 9,952 > 405) where the real n32s view had 149 um / 0 (COORD 08:20 DIE CHECKLIST).  The kit already
says where every pin goes; a stand-in must use it.

Kit pin plan sources, first found wins (all relative to the kit dir physical/ref_tile/<spec>/):
  1. spec.json "io_tcl" file, else io_pins.tcl, else assigned_io.tcl     place_pin -pin_name {p} -layer L -location {x y}
  2. assigned_pins.json   (opentallas.qwen.full-face-pins.v1: positions{port: {layer, xy_um[bit]}})
  3. spec.json "pins" faces {N: [ports], ...} spread evenly in order as tools/ref_tile/spread_face_pins.py does
     (bus bits in order, buses in face order, clocks centred; N/S alternate M3/M5, W/E M4)
Outline: spec.json outline {w, h}, else floorplan.json die.

  plan = load_plan(read, kit, port_widths)    read(rel_path) -> text | None;  port_widths {port: (width, is_vector)}
  plan['pins'][bit] = (face, t_um_along_face, layer);  place(plan, bit, w, h) -> (face, t scaled to w x h, layer)
  pin_rect(face, t, w, h, layer) -> (layer, rect) on the stand-in edge
"""
import json
import re

PIN_NAME = re.compile(r'-pin_name\s+(?:\{([^}]+)\}|(\S+))')
PIN_LAYER = re.compile(r'-layer\s+(\S+)')
PIN_LOC = re.compile(r'-location\s+\{\s*([-\d.]+)\s+([-\d.]+)\s*\}')
MARGIN = 4.32


class KitPinError(ValueError):
    pass


def _json(read, path):
    t = read(path)
    return json.loads(t) if t else None


def outline(read, kit, spec=None):
    spec = spec if spec is not None else (_json(read, f'{kit}/spec.json') or {})
    o = spec.get('outline') or {}
    if o.get('w') and o.get('h'):
        return float(o['w']), float(o['h'])
    fp = _json(read, f'{kit}/floorplan.json') or {}
    d = fp.get('die')
    if d and len(d) == 4:
        return float(d[2]) - float(d[0]), float(d[3]) - float(d[1])
    return None


def face_t(x, y, w, h):
    d = {'W': abs(x), 'E': abs(w - x), 'S': abs(y), 'N': abs(h - y)}
    f = min(d, key=d.get)
    return f, (y if f in 'WE' else x)


def parse_place_pin(text, w, h):
    pins = {}
    for ln in text.splitlines():
        if not ln.lstrip().startswith('place_pin'):
            continue
        n, la, lo = PIN_NAME.search(ln), PIN_LAYER.search(ln), PIN_LOC.search(ln)
        if not (n and la and lo):
            continue
        name, layer, x, y = (n.group(1) or n.group(2)).strip(), la.group(1), float(lo.group(1)), float(lo.group(2))
        f, t = face_t(x, y, w, h)
        pins[name] = (f, t, layer)
    return pins


def from_assigned(doc, w, h):
    pins = {}
    for port, v in (doc.get('positions') or {}).items():
        xy = v.get('xy_um') or []
        for k, (x, y) in enumerate(xy):
            f, t = face_t(float(x), float(y), w, h)
            pins[f'{port}[{k}]' if len(xy) > 1 else port] = (f, t, v.get('layer') or 'M4')
    return pins


def from_spec_faces(spec, port_widths, w, h, margin=MARGIN):
    faces = spec.get('pins')
    if not isinstance(faces, dict):
        return {}
    clocks = set(spec.get('clock_ports') or []) | ({spec['clock_port']} if spec.get('clock_port') else {'clk'})
    pins = {}
    for face, ports in faces.items():
        if face not in 'NSWE' or len(face) != 1:
            continue
        bits = []
        for p in ports:
            if p not in port_widths:
                continue                           # port renamed since the kit: left to the caller's fallback
            wd, vec = port_widths[p]
            bits += [f'{p}[{i}]' if vec else p for i in range(int(wd))]
        ck = [b for b in bits if b.split('[')[0] in clocks]
        if ck:
            bits = [b for b in bits if b not in ck]
            bits[len(bits) // 2:len(bits) // 2] = ck
        if not bits:
            continue
        horiz = face in 'NS'
        span = (w if horiz else h) - 2 * margin
        step = span / len(bits)
        for i, b in enumerate(bits):
            layer = ('M3' if i % 2 == 0 else 'M5') if horiz else 'M4'
            pins[b] = (face, margin + step * (i + 0.5), layer)
    return pins


def load_plan(read, kit, port_widths=None):
    """-> {source, kit, outline: (w, h), pins} or None when the kit has no pin plan / outline"""
    spec = _json(read, f'{kit}/spec.json')
    if spec is None:
        return None
    ol = outline(read, kit, spec)
    if not ol:
        return None
    w, h = ol
    cands = [spec.get('io_tcl'), f'{kit}/io_pins.tcl', f'{kit}/assigned_io.tcl']
    for c in cands:
        if not c:
            continue
        t = read(c)
        if t:
            pins = parse_place_pin(t, w, h)
            if pins:
                return dict(source=c, kit=kit, outline=ol, pins=pins)
    ap = _json(read, f'{kit}/assigned_pins.json')
    if ap:
        pins = from_assigned(ap, w, h)
        if pins:
            return dict(source=f'{kit}/assigned_pins.json', kit=kit, outline=ol, pins=pins)
    pins = from_spec_faces(spec, port_widths or {}, w, h)
    if pins:
        return dict(source=f'{kit}/spec.json:pins', kit=kit, outline=ol, pins=pins)
    return None


def place(plan, bit, w, h):
    """kit pin of `bit` scaled onto a w x h stand-in (same face, same fraction along it, same layer) or None"""
    r = plan['pins'].get(bit)
    if r is None:
        return None
    f, t, layer = r
    kw, kh = plan['outline']
    kl, sl = (kh, h) if f in 'WE' else (kw, w)
    return f, (t * sl / kl if kl else t), layer


def pin_rect(f, t, w, h, layer):
    if f in 'WE':
        t = min(max(t, 0.2), h - 0.2); xx = 0.0 if f == 'W' else w - 0.1
        return layer, (xx, t - 0.012, xx + 0.1, t + 0.012)
    t = min(max(t, 0.2), w - 0.2); yy = 0.0 if f == 'S' else h - 0.1
    return layer, (t - 0.012, yy, t + 0.012, yy + 0.1)
