#!/usr/bin/env python3
"""HBMc/CHAIN 10-22 (STEWARD-HBMc option A, CS pocket): reserved reset-stage home LATTICE for die_case_v16 --reserve-homes.

r18f S8: the reset forest found no legal hop home within reset reach in a dense lane-relay pocket below sm_SW4 (region CS,
(15080, 2131)): lane rows had filled every free cell, so the forest could not register the reset there (reach is NOT
relaxed).  GEN already supports reserved homes, marked BEFORE lane rows (a site on a block slides <= slide_um into free
area, carved channels included, else it is lost).  This tool emits one forest-tile-sized site (32.4 um, hbfd_rrl_hop/sync)
on a square lattice of pitch P over the die, so every point of free area is within P/sqrt(2) of a reserved home.

  reset_home_lattice.py --die W H --pitch 216 --out sites.json [--site 32.4] [--slide 108] [--margin 64.8]

Pitch default 216 um: < the forest hop budget (405 reach - relay radii - grid) by > 2x, so a lost or slid site never
leaves a reach gap on its own.  Sites are reservations only (no instance); the forest consumes them as free homes.
"""
import argparse
import json
from pathlib import Path


def lattice(W, H, pitch, site=32.4, slide=108.0, margin=64.8):
    sites = []
    nx = int((W - 2 * margin - site) // pitch) + 1
    ny = int((H - 2 * margin - site) // pitch) + 1
    x0 = (W - (nx - 1) * pitch - site) / 2
    y0 = (H - (ny - 1) * pitch - site) / 2
    for j in range(ny):
        for i in range(nx):
            sites.append(dict(name=f'rhl_{i:03d}_{j:03d}', x=round(x0 + i * pitch, 3), y=round(y0 + j * pitch, 3),
                              w=site, h=site, kind='hop', slide_um=slide,
                              why=f'reset home lattice pitch {pitch} um (forest hop homes in dense lane-relay pockets)'))
    return sites


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die', nargs=2, type=float, required=True, metavar=('W', 'H'))
    ap.add_argument('--pitch', type=float, default=216.0)
    ap.add_argument('--site', type=float, default=32.4)
    ap.add_argument('--slide', type=float, default=108.0)
    ap.add_argument('--margin', type=float, default=64.8)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    s = lattice(a.die[0], a.die[1], a.pitch, a.site, a.slide, a.margin)
    a.out.write_text(json.dumps(dict(schema='opentallas.hbm.reserve_homes.v1', pitch_um=a.pitch, sites=s), indent=1) + '\n')
    print('RESET_HOME_LATTICE sites', len(s), 'pitch', a.pitch, 'site', a.site, 'out', a.out)


if __name__ == '__main__':
    main()
