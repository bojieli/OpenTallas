#!/usr/bin/env python3
"""HBMc/CHAIN 10-22 (STEWARD-HBMc option A, CS pocket): reserved reset-stage home LATTICE for die_case_v16 --reserve-homes.

r18f S8: the reset forest found no legal hop home within reset reach in a dense lane-relay pocket below sm_SW4 (region CS,
(15080, 2131)): lane rows had filled every free cell, so the forest could not register the reset there (reach is NOT
relaxed).  GEN already supports reserved homes, marked BEFORE lane rows (a site on a block slides <= slide_um into free
area, carved channels included, else it is lost).  This tool emits one forest-tile-sized site (32.4 um, hbfd_rrl_hop/sync)
on a square lattice of pitch P over the die, so every point of free area is within P/sqrt(2) of a reserved home.

  reset_home_lattice.py --die W H --pitch 216 --out sites.json [--site 32.4] [--slide 108] [--margin 64.8]
  reset_home_lattice.py --need --manifest case/manifest.json --views V --relay-views RV --pitch 216 --out sites.json

--need (STEWARD-HBMc 10-22, case_bA2, the release candidate): only the lattice points that NEED a reserved home: no free
32.4 um home centre within --need-radius (Manhattan, default budget/2 = half the forest hop budget, so a chain through the
point always finds a hop home) on the given GEN geometry (blocks minus carved channels + lane-row relays), while one
WOULD exist with the lane-row relays removed (the lane rows filled the pocket -- the r18f CS case).  Points with no home
even without relays (inside unchanneled blocks) are not reserved: a site there would only be lost.  The full lattice
(18,240 sites at 216 um on r18f, 19.15 mm2) is the upper bound.

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


def need(manifest, views, relay_views, pitch, site=32.4, slide=108.0, margin=64.8, reach=405.0, radius=None,
         relays='hbfd_(rly|lh|land)'):
    """-> (sites, stats).  grid = homes with blocks + lane relays; rgrid = blocks only (reset_forest_geometry overfly)."""
    import numpy as np
    from scipy.ndimage import distance_transform_cdt
    from reset_forest_geometry import Geometry, GRID
    g = Geometry(manifest, views, relay_views, reach, overfly=relays)
    R = (g.budget / 2) if radius is None else radius
    nx, ny = g.grid.nx, g.grid.ny
    blk_all = np.frombuffer(bytes(g.grid.blk), dtype=np.uint8).reshape(ny, nx)
    blk_blk = np.frombuffer(bytes(g.rgrid.blk), dtype=np.uint8).reshape(ny, nx)
    d_all = distance_transform_cdt(blk_all, metric='taxicab') * GRID
    d_blk, (nj, ni) = distance_transform_cdt(blk_blk, metric='taxicab', return_indices=True)
    d_blk = d_blk * GRID
    W, H = manifest['die_um']
    full = lattice(W, H, pitch, site, slide, margin)
    nohome = []
    sites, st = [], dict(lattice=len(full), no_home_even_without_relays=0, home_in_reach=0)
    for s_ in full:
        cx, cy = s_['x'] + site / 2, s_['y'] + site / 2
        i, j = min(nx - 1, int(cx // GRID)), min(ny - 1, int(cy // GRID))
        if d_all[j, i] <= R:
            st['home_in_reach'] += 1
        elif d_blk[j, i] > R:
            st['no_home_even_without_relays'] += 1
            nohome.append([round(cx, 2), round(cy, 2)])
        else:
            # case_bA2 GEN: 109 of 216 lattice-point sites were LOST (the GEN slides a site <= slide_um off a block;
            # the free home was up to R away).  Snap the site onto the nearest block-free home centre instead.
            hx, hy = (ni[j, i] + .5) * GRID, (nj[j, i] + .5) * GRID
            s_ = dict(s_, x=round(hx - site / 2, 3), y=round(hy - site / 2, 3), lattice_xy=[s_['x'], s_['y']])
            s_ = dict(s_, why=f'need-only reset home: no free home within {R:.1f} um (lane relays filled it; '
                              f'{d_all[j, i]:.0f} um with relays, {d_blk[j, i]:.0f} um without)')
            sites.append(s_)
    st.update(need=len(sites), radius_um=round(R, 2), budget_um=round(g.budget, 2), overflown_relays=g.overflown_count,
              area_mm2=round(len(sites) * site * site / 1e6, 4), die_mm2=round(W * H / 1e6, 2),
              full_area_mm2=round(len(full) * site * site / 1e6, 4))
    st['no_home_points'] = nohome   # for the forest replay check: none may sit on a reset path the forest needs
    return sites, st


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die', nargs=2, type=float, metavar=('W', 'H'))
    ap.add_argument('--need', action='store_true')
    ap.add_argument('--manifest', type=Path)
    ap.add_argument('--views', type=Path)
    ap.add_argument('--relay-views', type=Path)
    ap.add_argument('--need-radius', type=float, default=None)
    ap.add_argument('--pitch', type=float, default=216.0)
    ap.add_argument('--site', type=float, default=32.4)
    ap.add_argument('--slide', type=float, default=108.0)
    ap.add_argument('--margin', type=float, default=64.8)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.need:
        s, st = need(json.loads(a.manifest.read_text()), a.views, a.relay_views, a.pitch, a.site, a.slide, a.margin,
                     radius=a.need_radius)
        a.out.write_text(json.dumps(dict(schema='opentallas.hbm.reserve_homes.v1', pitch_um=a.pitch, mode='need',
                                         stats=st, sites=s), indent=1) + '\n')
        print('RESET_HOME_NEED', json.dumps(st), 'out', a.out)
        return
    if not a.die:
        ap.error('--die W H is required without --need')
    s = lattice(a.die[0], a.die[1], a.pitch, a.site, a.slide, a.margin)
    a.out.write_text(json.dumps(dict(schema='opentallas.hbm.reserve_homes.v1', pitch_um=a.pitch, sites=s), indent=1) + '\n')
    print('RESET_HOME_LATTICE sites', len(s), 'pitch', a.pitch, 'site', a.site, 'out', a.out)


if __name__ == '__main__':
    main()
