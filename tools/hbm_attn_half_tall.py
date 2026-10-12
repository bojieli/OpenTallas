#!/usr/bin/env python3
"""hbmdie-1011 (die lead decision 10-11, main: taller attention halves instead of ceding M8 to them): derive TALLER
attention half records from physical/hbm_attn_tile_r/half_ps.

  physical/hbm_attn_tile_r/half_tall/hfd_attn_half_{lo,hi}/{ports.json, io_place.tcl}

The R25GQ band between the S and N attention row pairs (y 11,923-13,841 um, W side empty, E side only the host wire
chain) gives every tile (lo + hi) 1,892.16 um instead of 1,503.36 (+25.9 %); widths are unchanged.  Pin rule (faces
and pin order unchanged): pins on the S face and on the W / E faces keep their coordinates; pins on the N face move up
by the half's height increase (they stay on the N edge).  The seam buses xp / xr therefore stay face to face (lo N
face / hi S face).  Heights default to the proportional split of 1,892.16 (lo 1,024.92 / hi 867.24, on the 0.27 /
0.054 GY grid used by the die).  The half floorplans themselves are re-hardened by el1011-hbm-attn at this outline.

    python3 tools/hbm_attn_half_tall.py [--lo 1024.92 --hi 867.24]
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, DST = ROOT / 'physical/hbm_attn_tile_r/half_ps', ROOT / 'physical/hbm_attn_tile_r/half_tall'
PIN = re.compile(r'(place_pin -pin_name \{(\w+)\[(\d+)\]\} -layer \w+ -location \{[\d.]+ )([\d.]+)(\} .*)')


def north_ports(rec):
    """ports on the N face (horizontal run in the upper half), as split_attn classifies faces"""
    W_, H_ = rec['w_um'], rec['h_um']
    out = set()
    for p, v in rec['ports'].items():
        (x0, x1), (y0, y1) = v['x'], v['y']
        if x0 != x1 and y0 >= H_ / 2:
            out.add(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lo', type=float, default=1024.92)
    ap.add_argument('--hi', type=float, default=867.24)
    a = ap.parse_args()
    for h, new_h in (('lo', a.lo), ('hi', a.hi)):
        m = f'hfd_attn_half_{h}'
        rec = json.loads((SRC / m / 'ports.json').read_text())
        dh = round(new_h - rec['h_um'], 4)
        assert dh >= 0, (m, new_h, rec['h_um'])
        north = north_ports(rec)
        for p in north:
            rec['ports'][p]['y'] = [round(y + dh, 4) for y in rec['ports'][p]['y']]
        old_h = rec['h_um']
        rec['h_um'] = new_h
        rec['note_hbmdie_1011'] = (f'taller slot (die lead 10-11): h {old_h} -> {new_h} um (+{dh}); N-face ports '
                                   f'{sorted(north)} moved up by {dh} um, S / W / E pins unchanged; tools/hbm_attn_half_tall.py')
        lines, moved = [], 0
        for ln in (SRC / m / 'io_place.tcl').read_text().splitlines():
            mm = PIN.fullmatch(ln)
            if ln.startswith('#'):
                ln = ln.replace(f'x {old_h:.2f}', f'x {new_h:.2f}') + ' (half_tall: tools/hbm_attn_half_tall.py)'
            if mm and mm.group(2) in north:
                ln = f'{mm.group(1)}{float(mm.group(4)) + dh:.4f}{mm.group(5)}'
                moved += 1
            lines.append(ln)
        (DST / m).mkdir(parents=True, exist_ok=True)
        (DST / m / 'ports.json').write_text(json.dumps(rec, indent=1) + '\n')
        (DST / m / 'io_place.tcl').write_text('\n'.join(lines) + '\n')
        print(m, 'h', old_h, '->', new_h, 'N ports', sorted(north), 'pins moved', moved)


if __name__ == '__main__':
    main()
