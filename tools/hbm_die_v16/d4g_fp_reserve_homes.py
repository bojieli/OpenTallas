#!/usr/bin/env python3
"""L2H-GEN2D-FP2 10-19 (LEAD3-HBM decisions 23:22): RESERVED reset-stage homes for the GEN2d widened-channel floorplans.

Writes the --reserve-homes JSON consumed by tools/hbm_die_v15/die_case_v16.py.  Every site is an EMPTY rectangle (lower-left
x/y, w, h in um) that die_case marks before lane rows are placed, so the 624-bit lane relays cannot fill it; the manifest
placement leaves it empty, so reset_forest_layer.py sees it as a free stage home (its Geometry blocks only placed outlines).
Sites are derived from the GRANT slots of the variant (so a shifted floorplan moves its sites with it):

  --channels (fprsv): per quadrant, in the sfucore <-> hb_dbk/hc channel (NW/SW: east of the sfucore east face; NE/SE: west of
     the sfucore west face), 10.8 um off the sfucore pin face (halo), one 25.92 x 19.44 um site every CH_PITCH = 270 um along
     the sfucore height (<= the ~370 um stage pitch, so a 405 um reach hop always has a home in the channel), plus the stream
     regional-root site (GEN2d stream NW root try 0 = (8702, 21648) = sfucore_NW east face + 778 um, sfucore base + 857 um;
     mirrored per quadrant by the sfucore orientation) as a 38.88 x 19.44 um sync + first-hop site, and one hop site midway
     between the root site and the channel.
  always (fp86 and fprsv): the hbm reset-sync grant slots in the PHY-SM strip: a 25.92 x 19.44 um site (12.96 x 6.48 um
     hard hbfd_rrl sync tile + 6.48 um halo per side) 10.8 um below/above the SM frame edge under sm_<SW|NW>3 at the hbm SW
     regional-root x (9490: 'no legal sync home near (9490, 2656)', the root falls inside sm_SW3) and under sm_<SW|NW>4 at
     x = 11498 ('no legal reset relay ... from (11498, 2048)'), mirrored N/S, and under/above sm_<SW|NW>7 (the E-zone hbm
     roots) at the same offsets from the SM column origin.

Usage: d4g_fp_reserve_homes.py grants.json out.json [--channels] [--tag TAG]
"""
import argparse
import json

TILE_W, TILE_H = 12.96, 6.48          # closed hard hbfd_rrl sync/hop footprint (relay_views_hard)
SITE_W, SITE_H = 25.92, 19.44         # tile + 6.48 um halo per side (>= tile + 10 um forest GRID: one legal centre always)
ROOT_W = 38.88                        # sync + first hop side by side + halo
FACE_HALO = 10.8                      # die_case HALO off a pin face
CH_PITCH = 270.0
ROOT_DX, ROOT_DY = 778.0, 857.0       # stream NW root try 0 relative to sfucore_NW east face / base (MX)
HBM_X = {3: 9490.0 - 7960.248, 4: 11498.0 - 10299.96}   # offsets from the SM column origin (sm_SW3 / sm_SW4 grants)


def site(name, x, y, w, h, kind, why, slide=43.2):
    return dict(name=name, x=round(x, 3), y=round(y, 3), w=w, h=h, kind=kind, slide_um=slide, why=why)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('grants'); ap.add_argument('out')
    ap.add_argument('--channels', action='store_true')
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    g = json.load(open(a.grants)); S = {s['name']: s for s in g['slots']}
    out = []
    if a.channels:
        for q in ('NW', 'SW', 'NE', 'SE'):
            sf = S[f'sfucore_{q}']; o = sf['origin']; ow = sf['outline']
            east = q.endswith('W')                          # NW/SW channel is east of sfucore, NE/SE west of it
            face = o['x'] + ow['w'] if east else o['x']
            x0 = face + FACE_HALO if east else face - FACE_HALO - SITE_W
            n = int(ow['h'] // CH_PITCH) + 1
            for k in range(n):
                cy = o['y'] + CH_PITCH / 2 + k * CH_PITCH
                if cy > o['y'] + ow['h']:
                    break
                out.append(site(f'rsv_ch_{q}_{k}', x0, cy - SITE_H / 2, SITE_W, SITE_H, 'stream_channel_hop',
                                f'stream reset stage home in the sfucore_{q} <-> hb_dbk/hc channel, pitch {CH_PITCH} um'))
            mx = o.get('orient', 'R0') in ('MX', 'R180')    # NW (MX) is the measured basis; SW (R0) mirrors in y
            ry = o['y'] + (ROOT_DY if mx else ow['h'] - ROOT_DY)
            rx = face + ROOT_DX if east else face - ROOT_DX
            out.append(site(f'rsv_root_{q}', rx - ROOT_W / 2, ry - SITE_H / 2, ROOT_W, SITE_H, 'stream_root_sync',
                            f'stream {q} regional root (sync + first hop); NW basis = GEN2d stream NW root try 0 (8702, 21648)',
                            slide=86.4))
            mxx = (rx + face) / 2
            out.append(site(f'rsv_mid_{q}', mxx - SITE_W / 2, ry - SITE_H / 2, SITE_W, SITE_H, 'stream_root_hop',
                            f'stream {q} hop between the root site and the channel ({abs(rx - face) / 2:.0f} um from each)'))
    for half in ('S', 'N'):
        for col in (3, 4, 7):
            sm = S[f'sm_{half}W{col}']; o = sm['origin']; ow = sm['outline']
            offs = [HBM_X[col]] if col in HBM_X else [HBM_X[3], HBM_X[4]]
            for k, off in enumerate(offs):
                cx = o['x'] + off
                y0 = o['y'] - FACE_HALO - SITE_H if half == 'S' else o['y'] + ow['h'] + FACE_HALO
                out.append(site(f'rsv_hbm_sync_{half}{col}_{k}', cx - SITE_W / 2, y0, SITE_W, SITE_H, 'hbm_sync_grant',
                                f'hbm reset-sync grant slot in the PHY-SM strip by sm_{half}W{col} (12.96x6.48 hard tile + halo); '
                                f'basis: hhKR hbm SW rejects at (9490, 2656) / (11498, 2048)', slide=43.2))
    doc = dict(schema='opentallas.hbm.reserved_reset_homes.v1', tag=a.tag, grants=a.grants, tile_um=[TILE_W, TILE_H],
               decision='LEAD3-HBM 10-19 23:22 (1b fprsv reserved homes, 2 hbm SW hard sync slot x4)', sites=out)
    json.dump(doc, open(a.out, 'w'), indent=1)
    print('RESERVE_HOMES', len(out), dict((k, sum(1 for s in out if s['kind'] == k)) for k in sorted({s['kind'] for s in out})))


if __name__ == '__main__':
    main()
