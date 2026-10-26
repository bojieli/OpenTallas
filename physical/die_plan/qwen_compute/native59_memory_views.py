"""Physical views of the eight native59 Q-seat writer SRAMs (qfd_native59_qseat_lanes g_writer[0..7].u_mem).

PATH-QC-N59 (10-25, COORD ruling B 11:31) supersedes Codex's c3d06bcdcf / 45e3f3a3c7 draft (NOT_READY: wrong
orientation, no pin-track offset):
  * the macro is ot_sram_1r1w_32x512_m1 regenerated with 16 lane write enables (mem_compiler mask_gran 32,
    pin_faces "rw"): master LEFT edge = clk + read port (r_ce_in, r_addr_in, rd_out[511:0]); master RIGHT edge = write
    port (w_ce_in, w_addr_in, then wd_in[32k +: 32], w_mask_in[k] per lane group k).  Size from the macro datasheet.
  * two columns around the central read-mux / clock corridor: the LEFT column is MY (read pins mirrored to its right
    edge, facing the corridor; write pins on its outer, west edge), the RIGHT column is R0 (read pins on its left edge,
    facing the corridor; write pins on its outer, east edge).
  * origins = 8.64-um lattice + 0.012 um in x and y: the macro's M4 pin centres sit at 0.012 mod 0.048 of the macro
    frame, the plan's M4 / M5 tracks at 0.024 + 0.048 k (schema layer table, offset = pitch / 2), so a lattice origin
    puts every pin half a track off; +0.012 centres all 1,053 pins on tracks in both orients (pin_track_audit()).
    contents[] origins carry the shift themselves (gen_phys.type_macros applies track_offset_um to hard_cores only).
No RTL cycles change: the macros are the eight 32 x 512 writer banks already in the RTL.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = 'ot_sram_1r1w_32x512_m1'
MACRO_DIR = f'physical/asap7_memory_macros/{MODULE}'
PREFIX = 'u_bound.u_core.u_qb.u_qseat'          # synthesized instance path (native59 preflight 1_2_yosys.v, Codex 07:19)
LATTICE = 8.64
PIN_SHIFT = 0.012
COLS = (77.76, 527.04)                           # x of the left (MY) and right (R0) column, lattice
ROWS = (43.2, 146.88, 259.2, 371.52)             # y of the four rows, lattice (rows kept from the 07:19 review)


def macro_size(root: Path = ROOT) -> tuple[float, float]:
    a = json.loads((root / MACRO_DIR / f'{MODULE}.json').read_text())['area']
    return a['macro_width_um'], a['macro_height_um']


def entries(root: Path = ROOT) -> list[dict]:
    w, h = macro_size(root)
    out = []
    for i in range(8):
        col, row = i // 4, i % 4
        x, y = COLS[col] + PIN_SHIFT, ROWS[row] + PIN_SHIFT
        out.append(dict(inst=f'{PREFIX}.g_writer[{i}].u_mem', module=MODULE, status='reuse',
                        outline_um=[w, h], origin_um=[round(x, 3), round(y, 3)], orient=('MY', 'R0')[col],
                        lef=f'{MACRO_DIR}/{MODULE}.lef', lib=f'{MACRO_DIR}/{MODULE}_tt.lib',
                        note='native59 writer bank (16 lane write enables); read port faces the central corridor, '
                             'write port the outer channel; origin = lattice + 0.012 um (pins on M4/M5 tracks); '
                             '0 added cycles'))
    return out


def attach(raw: dict, root: Path = ROOT) -> list[dict]:
    t = raw['partition_types']['native59']
    w, h = t['outline_um']
    es = entries(root)
    for e in es:
        x, y = e['origin_um']
        mw, mh = e['outline_um']
        assert 0 < x and x + mw < w and 0 < y and y + mh < h, (e['inst'], x, y, w, h)
    names = {e['inst'] for e in es}
    t['contents'] = [c for c in t['contents'] if c['inst'] not in names] + es
    return es


def lef_pins(path: Path) -> list[tuple[str, str, tuple[float, float, float, float]]]:
    """(pin, layer, rect) of every signal pin of the LEF."""
    pins, name, layer = [], None, None
    for line in path.read_text().splitlines():
        s = line.split()
        if not s:
            continue
        if s[0] == 'PIN' and s[1] not in ('VDD', 'VSS'):
            name = s[1]
        elif s[0] == 'END' and len(s) > 1 and s[1] == name:
            name = None
        elif name and s[0] == 'LAYER':
            layer = s[1]
        elif name and s[0] == 'RECT':
            pins.append((name, layer, tuple(float(v) for v in s[1:5])))
    return pins


def _xf(rect, orient, w, h):
    x1, y1, x2, y2 = rect
    if orient == 'MY':
        x1, x2 = w - x2, w - x1
    elif orient == 'MX':
        y1, y2 = h - y2, h - y1
    elif orient == 'R180':
        x1, x2, y1, y2 = w - x2, w - x1, h - y2, h - y1
    return x1, y1, x2, y2


def pin_track_audit(es: list[dict], track_offset: float = 0.024, pitch: float = 0.048,
                    root: Path = ROOT) -> dict:
    """Every signal pin of every placed macro: its M4 centre-line y on an M4 track and an M5 track x inside its
    rect (the plan layer table: M4 / M5 offset 0.024, pitch 0.048).  Returns counts and the first failures."""
    pins = lef_pins(root / MACRO_DIR / f'{MODULE}.lef')
    bad, n, faces = [], 0, {}
    for e in es:
        w, h = e['outline_um']
        ox, oy = e['origin_um']
        for name, layer, r in pins:
            x1, y1, x2, y2 = _xf(r, e['orient'], w, h)
            x1, x2, y1, y2 = ox + x1, ox + x2, oy + y1, oy + y2
            n += 1
            yc = (y1 + y2) / 2
            ky = (yc - track_offset) / pitch
            on_y = abs(ky - round(ky)) * pitch < 1e-4
            kx = math.ceil((x1 - track_offset) / pitch - 1e-6)
            on_x = track_offset + kx * pitch <= x2 + 1e-6
            if not (on_y and on_x):
                bad.append(dict(inst=e['inst'], pin=name, rect=[round(v, 4) for v in (x1, y1, x2, y2)],
                                y_off_track_um=round((ky - round(ky)) * pitch, 4), m5_in_rect=on_x))
            side = 'W' if x1 < ox + w / 2 else 'E'
            key = (e['inst'], 'rd' if name.startswith(('rd_out', 'r_', 'clk')) else 'wr')
            faces.setdefault(key, set()).add(side)
    return dict(pins_checked=n, off_track=len(bad), first_failures=bad[:5],
                faces={f'{k[0]}:{k[1]}': sorted(v) for k, v in sorted(faces.items())})


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('plan', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--audit', type=Path, help='write the pin-track audit JSON here')
    a = ap.parse_args()
    raw = json.loads(a.plan.read_text())
    es = attach(raw)
    a.out.write_text(json.dumps(raw, separators=(',', ':')) + '\n')
    rep = pin_track_audit(es)
    if a.audit:
        a.audit.write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('pins_checked', 'off_track', 'first_failures')}))
