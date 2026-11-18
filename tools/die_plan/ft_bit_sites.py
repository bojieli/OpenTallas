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
