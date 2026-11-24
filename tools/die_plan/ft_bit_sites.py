"""Serialize optional FT per-bit cell lower-left sites (internal j=1 by default).

Each stage has width+1 sites: payload bits then the epoch bit.  Cell footprints
are allocation envelopes, checked against each real master by face_flops.tcl.
"""
import math


def validate_slot(slot):
    sites = slot.get('bit_sites_um')
    if sites is None:
        if 'bit_site_cell_um' in slot:
            raise ValueError('bit_site_cell_um requires bit_sites_um')
        return
    cell = slot.get('bit_site_cell_um')
    if not cell or len(cell) != 2 or any(not math.isfinite(v) or v <= 0 for v in cell):
        raise ValueError('bit_sites_um requires positive bit_site_cell_um footprint')
    count = slot.get('stations', 1)
    if len(sites) != count - 1 and not (slot.get('explicit_stage0') is True and len(sites) == count):
        raise ValueError('bit_sites_um must contain stations-1 internal stages, or stations with explicit_stage0')
    for stage in sites:
        if len(stage) != slot['width'] + 1:
            raise ValueError('each bit_sites_um stage must contain width+1 payload/epoch sites')
        if any(len(xy) != 2 or any(not math.isfinite(v) for v in xy) for xy in stage):
            raise ValueError('bit_sites_um coordinates must be finite x/y pairs')


def snap_slots(slots, origin, site_w=0.054, row_h=0.27):
    """FIX-S81-VPW 11-17 (FABLE-CLOSURE-STRATEGY lever 6.2): snap every explicit bit site (cell lower-left) to the
    nearest site column / row of the core grid starting at origin (kit core xMin/yMin, um).  A re-sited plan stage
    (S81 leaf t7 ft3 82.9376 176.8544, t53 ft0 9.3393 1032.3389) was off the grid, which face_flops.tcl refuses
    ("explicit FT site is not on a row/site").  A move is at most half a site in x and half a row in y; two sites of
    the type that snap onto one grid point raise.  -> (slots, moved count); slots without bit_sites_um unchanged."""
    x0, y0 = map(float, origin)
    out, moved, seen = [], 0, {}
    for slot in slots:
        if not slot.get('bit_sites_um'):
            out.append(slot)
            continue
        stages = []
        for j, stage in enumerate(slot['bit_sites_um']):
            st = []
            for bit, (x, y) in enumerate(stage):
                c, r = round((float(x) - x0) / site_w), round((float(y) - y0) / row_h)
                q = [round(x0 + c * site_w, 6), round(y0 + r * row_h, 6)]
                if abs(q[0] - x) > 5e-4 or abs(q[1] - y) > 5e-4:   # > half a dbu: a real move, not float noise
                    moved += 1
                if (c, r) in seen:
                    raise ValueError(f"FT bit sites {seen[(c, r)]} and {slot['name']},{j},{bit} snap to one site {q}")
                seen[(c, r)] = f"{slot['name']},{j},{bit}"
                st.append(q)
            stages.append(st)
        out.append(dict(slot, bit_sites_um=stages))
    return out, moved


def table(slots):
    lines = ['# Generated explicit FT cell lower-left sites (um); stage j starts at 1.',
             'set ff_bit_sites {}', 'set ff_bit_site_cells {}']
    for slot in slots:
        validate_slot(slot)
        if 'bit_sites_um' not in slot:
            continue
        name = slot['name']
        w, h = slot['bit_site_cell_um']
        lines.append(f'dict set ff_bit_site_cells {{{name}}} {{{w:.9g} {h:.9g}}}')
        # A complete stage0 table is accepted only through the existing opt-in.
        first = 0 if len(slot['bit_sites_um']) == slot.get('stations', 1) else 1
        for j, stage in enumerate(slot['bit_sites_um'], first):
            for bit, (x, y) in enumerate(stage):
                lines.append(f'dict set ff_bit_sites {{{name},{j},{bit}}} {{{x:.9g} {y:.9g}}}')
    return '\n'.join(lines) + '\n'


def _cells(w, h, site_w, row_h):
    """footprint (um) -> (site columns, rows) it covers on the core grid."""
    return max(1, math.ceil(w / site_w - 1e-6)), max(1, math.ceil(h / row_h - 1e-6))


def footprint_conflicts(slots, origin, site_w=0.054, row_h=0.27, fixed=()):
    """QC-SUC-FTSITE 11-24: census of explicit FT bit footprints (bit_site_cell_um) that overlap once snapped to the
    core grid, across every slot and stage of one type.  snap_slots only refuses two sites on ONE grid point; a 0.084 um
    y pitch (su_c cws1/cws2 stage 0, a y-compression row map) or a 0.054 um x step overlaps cells that land on different
    grid points.  fixed = extra (label, x, y, w, h) footprints (internal-station sites) that count as occupied.
    -> list of (label_a, label_b) pairs, label = 'slot,stage,bit'."""
    x0, y0 = map(float, origin)
    occ, out = {}, []
    items = [(lab, x, y, w, h) for lab, x, y, w, h in fixed]
    for slot in slots:
        if not slot.get('bit_sites_um'):
            continue
        w, h = slot.get('bit_site_cell_um') or (1.404, 0.27)
        for j, stage in enumerate(slot['bit_sites_um']):
            for bit, (x, y) in enumerate(stage):
                items.append((f"{slot['name']},{j},{bit}", x, y, w, h))
    for lab, x, y, w, h in items:
        c, r = round((float(x) - x0) / site_w), round((float(y) - y0) / row_h)
        cw, rh = _cells(w, h, site_w, row_h)
        hit = None
        for rr in range(r, r + rh):
            for cc in range(c, c + cw):
                if (cc, rr) in occ:
                    hit = occ[(cc, rr)]
                    break
            if hit:
                break
        if hit:
            out.append((hit, lab))
            continue
        for rr in range(r, r + rh):
            for cc in range(c, c + cw):
                occ[(cc, rr)] = lab
    return out


def legalize_slots(slots, origin, core_box, blocks=(), fixed=(), site_w=0.054, row_h=0.27, radius_um=16.2):
    """QC-SUC-FTSITE 11-24: put every explicit FT bit site on the core grid with NO footprint overlap (positions only,
    0 cycles: stations, stage count, bit order, windows and pins unchanged).

    Pass 1 keeps each site unchanged when its snapped footprint (gen's snap_slots rounding) is free (slot, stage, bit order);
    pass 2 moves each conflicting bit to the nearest free grid site, x distance weighted 2:1 against y so a column
    grows into more rows before it spills sideways (ties: fewest site columns), inside core_box (x0, y0, x1, y1), off every block box (hard cores +
    halo) and off fixed footprints.  A column that holds more bits than its band rows therefore spreads to the
    adjacent rows / columns instead of packing below a row pitch.
    -> (slots, moves) where moves = [(label, [x, y] from, [x, y] to, manhattan um)]; raises if a bit has no free site
    within radius_um."""
    x0, y0 = map(float, origin)
    bx0, by0, bx1, by1 = map(float, core_box)
    occ = set()

    def cells_of(c, r, cw, rh):
        return [(cc, rr) for rr in range(r, r + rh) for cc in range(c, c + cw)]

    def legal(c, r, cw, rh, w, h):
        x, y = x0 + c * site_w, y0 + r * row_h
        if x < bx0 - 1e-6 or y < by0 - 1e-6 or x + w > bx1 + 1e-6 or y + h > by1 + 1e-6:
            return False
        if any(x < b2 and a < x + w and y < d and b < y + h for a, b, b2, d in blocks):
            return False
        return not any(k in occ for k in cells_of(c, r, cw, rh))

    for _, x, y, w, h in fixed:
        cw, rh = _cells(w, h, site_w, row_h)
        occ.update(cells_of(round((float(x) - x0) / site_w), round((float(y) - y0) / row_h), cw, rh))
    out = [dict(s, bit_sites_um=[[list(xy) for xy in st] for st in s['bit_sites_um']]) if s.get('bit_sites_um') else s
           for s in slots]
    pending = []
    for slot in out:
        if not slot.get('bit_sites_um'):
            continue
        w, h = slot.get('bit_site_cell_um') or (1.404, 0.27)
        cw, rh = _cells(w, h, site_w, row_h)
        for j, stage in enumerate(slot['bit_sites_um']):
            for bit, (x, y) in enumerate(stage):
                c, r = round((float(x) - x0) / site_w), round((float(y) - y0) / row_h)
                ks = cells_of(c, r, cw, rh)
                if any(k in occ for k in ks):
                    pending.append((slot, j, bit, c, r, cw, rh, w, h))
                    continue
                occ.update(ks)              # kept exactly as planned (gen snap_slots puts it on the grid point)
    nr, nc = int(radius_um / row_h), int(radius_um / site_w)
    offs = sorted(((2 * abs(dc) * site_w + abs(dr) * row_h, abs(dc), abs(dr), dc, dr)
                   for dr in range(-nr, nr + 1) for dc in range(-nc, nc + 1)
                   if abs(dc) * site_w + abs(dr) * row_h <= radius_um + 1e-9))
    moves = []
    for slot, j, bit, c, r, cw, rh, w, h in pending:
        frm = list(slot['bit_sites_um'][j][bit])
        for d, _, _, dc, dr in offs:
            if legal(c + dc, r + dr, cw, rh, w, h):
                occ.update(cells_of(c + dc, r + dr, cw, rh))
                to = [round(x0 + (c + dc) * site_w, 6), round(y0 + (r + dr) * row_h, 6)]
                slot['bit_sites_um'][j][bit] = to
                moves.append((f"{slot['name']},{j},{bit}", frm, to, round(abs(to[0] - frm[0]) + abs(to[1] - frm[1]), 4)))
                break
        else:
            raise ValueError(f"FT bit site {slot['name']},{j},{bit} at {frm}: no free grid site within {radius_um} um")
    return out, moves
