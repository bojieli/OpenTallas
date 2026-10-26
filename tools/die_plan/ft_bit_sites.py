"""Serialize optional FT per-bit cell lower-left sites, internal stage first (j=1).

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
    if len(sites) != slot.get('stations', 1) - 1:
        raise ValueError('bit_sites_um must contain stations-1 internal stages')
    for stage in sites:
        if len(stage) != slot['width'] + 1:
            raise ValueError('each bit_sites_um stage must contain width+1 payload/epoch sites')
        if any(len(xy) != 2 or any(not math.isfinite(v) for v in xy) for xy in stage):
            raise ValueError('bit_sites_um coordinates must be finite x/y pairs')


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
        for j, stage in enumerate(slot['bit_sites_um'], 1):
            for bit, (x, y) in enumerate(stage):
                lines.append(f'dict set ff_bit_sites {{{name},{j},{bit}}} {{{x:.9g} {y:.9g}}}')
    return '\n'.join(lines) + '\n'
