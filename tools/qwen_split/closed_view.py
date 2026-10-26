"""Q-NETLIST 2026-10-16: die frames from a master's hardened view.

The compute-die generator drew qfd_rstseq (54 x 54) and qfd_rstsync (54 x 32.4) as historical generated frames while
their hard leaves were closed at 21.6 x 21.6 (FILL-Q r3, tools/ref_tile/specs_qrst), so bind_real refused both views
('outline: case 53.976 x 53.976, view 21.6 x 21.6') and the die ran a generated frame instead of the real abstract.
The structural fix is to size the die slot from the view (the view is the physical truth; growing the leaf to the old
frame would re-open a closed element): view_frame() returns the view's outline and every signal pin (face, layer,
along-face coordinate) so the die master is drawn exactly as the abstract that bind_real swaps in.

Q-VIEWFRAME 10-16: the same for the NEW-parent masters qfd_d2d_static (static link end, view r5 475.2 x 280.8 in a
777.576 x 518.376 slot) and qfd_res_train_issue (view c2 30.24 x 30.24 in a 129.6 slot).  Their view directories are not
physical/ref_tile/<m>/views/<m>: view_dir() follows bind_real's own search (the recorded bind_view_select.json choice
first, then the master's own directory, then the single physical/ref_tile/*/views/<m>), so the generator draws the very
view bind_real binds.  install_master() builds the die master from the RTL port list with every bit on its view pin
(port_join aliases are fragments of those pins); a die port without a view pin fails closed.
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PG = {'VDD', 'VSS'}
SELECT = 'results/arch/qwen_split_compute_1014/bind_view_select.json'


def enabled():
    return os.environ.get('OT_SPLIT_VIEW_FRAMES', '1') != '0'


def _select(root=ROOT):
    p = Path(os.environ.get('OT_BIND_VIEW_SELECT') or SELECT)
    p = p if p.is_absolute() else root / p
    return json.loads(p.read_text()).get('views', {}) if p.exists() else {}


def view_dir(master, root=ROOT):
    """the CLOSED view directory bind_real binds for this master (tools/qwen_tp8/bind_real.find_view order), or None"""
    sel = _select(root).get(master)
    if sel:
        d = Path(sel) if Path(sel).is_absolute() else root / sel
        if not (d / f'{master}.lef').exists():
            raise ValueError(f'{master}: selected view {sel} has no {master}.lef in this tree')
        return d
    d = root / 'physical/ref_tile' / master / 'views' / master
    if (d / f'{master}.lef').exists():
        return d
    c = [x for x in sorted((root / 'physical/ref_tile').glob(f'*/views/{master}')) if (x / f'{master}.lef').exists()]
    if len(c) > 1:
        raise ValueError(f'{master}: {len(c)} closed views ({", ".join(str(x.relative_to(root)) for x in c)}) and no '
                         f'choice in {SELECT}')
    return c[0] if c else None


def view_lef(master, root=ROOT):
    d = view_dir(master, root)
    return d / f'{master}.lef' if d is not None else None


def parse_frame(text, master):
    """(w, h, {pin: (face, layer, coordinate_um)}) from LEF text; each pin is located by its rectangle on the outline"""
    m = re.search(rf'^MACRO {re.escape(master)}[ \t]*$(.*?)^END {re.escape(master)}[ \t]*$', text, re.M | re.S)
    if not m:
        return None
    body = m.group(1)
    w, h = (float(x) for x in re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', body).groups())
    pins = {}
    for pm in re.finditer(r'^\s*PIN (\S+)\s*$(.*?)^\s*END \1\s*$', body, re.M | re.S):
        name, blk = pm.group(1), pm.group(2)
        if name in PG:
            continue
        best = None
        for lay, r in re.findall(r'LAYER (\S+)\s*;\s*RECT\s+([-\d.]+\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+)', blk):
            x0, y0, x1, y1 = map(float, r.split())
            d = {'W': x0, 'E': w - x1, 'S': y0, 'N': h - y1}
            face = min(d, key=d.get)
            z = (y0 + y1) / 2 if face in 'WE' else (x0 + x1) / 2
            if best is None or d[face] < best[0]:
                best = (d[face], face, lay, round(z, 4))
        if best is None:
            raise ValueError(f'{master}.{name}: view pin without a rectangle')
        if best[0] > 1e-3:
            raise ValueError(f'{master}.{name}: view pin not on the outline ({best[0]:.3f} um inside)')
        pins[name] = best[1:]
    return w, h, pins


def view_frame(master, root=ROOT):
    """(w, h, {pin: (face, layer, coordinate_um)}) of the hardened view, or None when the master has no view."""
    p = view_lef(master, root)
    return parse_frame(p.read_text(), master) if p is not None else None


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


def bit_pins(pins, port, n):
    """view pin names of RTL port `port` (n bits), LSB first.  A scalar port may be exported as a 1-bit bus (p[0]).
    Raises ValueError naming every bit without a view pin: never tied, never dropped."""
    if n == 1:
        for nm in (port, f'{port}[0]'):
            if nm in pins:
                return [nm]
        raise ValueError(f'die port {port} has no view pin ({port} / {port}[0])')
    names = [f'{port}[{b}]' for b in range(n)]
    miss = [nm for nm in names if nm not in pins]
    if miss:
        raise ValueError(f'die port {port}[{n - 1}:0]: {len(miss)} bits have no view pin ({", ".join(miss[:6])})')
    return names


def _rect(face, z, w, h, depth=.192, hw=.012):
    return {'W': (0.0, z - hw, depth, z + hw), 'E': (w - depth, z - hw, w, z + hw),
            'S': (z - hw, 0.0, z + hw, depth), 'N': (z - hw, h - depth, z + hw, h)}[face]


def install_master(M, model, Master, inst, mst, rtl, partition_master, note=''):
    """Die master `mst` of instance `inst` drawn exactly as its closed view: view outline, every RTL port bit on its
    view pin (face, layer, along-face position), port_join aliases as fragments of those pins.  rtl = rtl_ports()."""
    vd = view_dir(mst)
    if vd is None:
        raise ValueError(f'{mst}: no closed view in this tree')
    w, h, P = parse_frame((vd / f'{mst}.lef').read_text(), mst)
    if abs(inst.w - w) > 1e-3 or abs(inst.h - h) > 1e-3:
        raise ValueError(f'{mst}: instance {inst.name} {inst.w} x {inst.h} is not the view outline {w} x {h}')
    if model.get('port_split', {}).get(mst):
        raise ValueError(f'{mst}: port_split bundles on a view-framed master are not supported')
    aliases = model.get('port_join', {}).get(mst, {})
    covered = {real for real, _ in aliases.values()}
    unknown = sorted(r for r in covered if r not in rtl)
    if unknown:
        raise ValueError(f'{mst}: port_join aliases of non-RTL ports {unknown}')
    errs, used, bits = [], set(), {}
    for p, (n, _d) in rtl.items():
        try:
            bits[p] = bit_pins(P, p, n)
            used.update(bits[p])
        except ValueError as e:
            errs.append(str(e))
    extra = sorted(set(P) - used)
    if errs or extra:
        raise ValueError(f'{mst}: RTL / closed view {vd.relative_to(ROOT) if ROOT in vd.parents else vd} mismatch: '
                         f'{"; ".join(errs[:6])}{"; " if errs and extra else ""}'
                         f'{f"{len(extra)} view pins not in the RTL ({extra[:6]})" if extra else ""}')
    q = Master(mst, w, h, 7, note or f'closed view {vd.relative_to(ROOT) if ROOT in vd.parents else vd}: outline and '
               'every pin as the abstract bind_real binds')
    q.view_pin_layers = {}
    rects, scalar_bus = [], []
    for p, (n, _d) in rtl.items():
        geo = [P[nm] for nm in bits[p]]
        if n == 1 and bits[p][0] != p:
            scalar_bus.append(p)
        for b, (f, lay, z) in enumerate(geo):
            rects.append((p if n == 1 else f'{p}[{b}]', lay, _rect(f, z, w, h)))
        faces = {f for f, _, _ in geo}
        if len(faces) != 1:
            if p in covered:                                # fragments carry exact rectangles: any face is fine
                q.ports[p] = ('pins', n, None, None, [], 1)
                q.order.append(p)
                continue
            raise ValueError(f'{mst}.{p}: view bits on faces {sorted(faces)}; one die port needs one face')
        lays = [lay for _, lay, _ in geo]
        main = max(set(lays), key=lays.count)
        q.ports[p] = ('pins', n, geo[0][0], main, [z for _, _, z in geo], 1)
        q.order.append(p)
        if len(set(lays)) > 1:
            q.view_pin_layers[p] = lays
    if aliases:
        partition_master(q, aliases, rects)
    q.view_pin_layers = {p: v for p, v in q.view_pin_layers.items() if p in q.ports}
    M[mst] = q
    rec = dict(view=str(vd.relative_to(ROOT)) if ROOT in vd.parents else str(vd), outline_um=[w, h],
               rtl_ports=len(rtl), pins_mapped=len(used), aliases=len(aliases),
               mixed_layer_ports=sorted(q.view_pin_layers), scalar_ports_on_1bit_view_bus=scalar_bus)
    model.setdefault('view_frames', {})[mst] = rec
    return rec
