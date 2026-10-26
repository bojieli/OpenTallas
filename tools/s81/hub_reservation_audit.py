#!/usr/bin/env python3
"""S81 vmc hub reservation audit (S-DIE-26B 10-16): every hub block of a --hub-layout record, its MIX4 slot, the
canonical record's actual hard boxes (SW PHY/CTRL/SVC, links, svcj), the six HCP homes and all 128 field frames:
zero pairwise overlap and nothing outside the die (same 160-box check as vmc_2330/nt_reservation_audit.json).

Geometry only: no native parent, route, GRT or timing claim.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIE = (33000.0, 26000.0)


def rel(p):
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def boxes_of(layout, canonical):
    out = {k: list(v[:4]) for k, v in layout['blocks'].items()}
    hub = set(out)
    for f in canonical['hard_fixed_boxes']:
        if f[0] not in hub and not f[0].startswith('sp_'):   # the canonical record's old hub boxes are superseded
            out[f[0]] = list(f[1:5])
    out['MIX4'] = list(layout['mix4_slot'])
    for h in canonical['hcp_homes']:
        out[h['name']] = [*h['at_um'], h['outline']['w'], h['outline']['h']]
    for f in canonical['placements']:
        out[f'frame_{f["root"]}'] = [*f['origin_um'], *f['outline_um']]
    return out


def audit(layout_path, canonical_path):
    lay = json.loads(rel(layout_path).read_text())
    can = json.loads(rel(canonical_path).read_text())
    bx = boxes_of(lay, can)
    names = sorted(bx)
    coll = []
    for i, a in enumerate(names):
        p = bx[a]
        for b in names[i + 1:]:
            q = bx[b]
            if p[0] < q[0] + q[2] - 1e-6 and q[0] < p[0] + p[2] - 1e-6 and p[1] < q[1] + q[3] - 1e-6 and q[1] < p[1] + p[3] - 1e-6:
                coll.append([a, b])
    outside = [n for n in names if bx[n][0] < -1e-6 or bx[n][1] < -1e-6 or bx[n][0] + bx[n][2] > DIE[0] + 1e-6
               or bx[n][1] + bx[n][3] > DIE[1] + 1e-6]
    b = lay['blocks']
    vm, co, hc, ca, ga = b['sp_vm'], b['sp_collective'], b['sp_hc_s'], b['sp_capture'], b['sp_gather']
    return dict(scope='HELD_RESERVATION_GEOMETRY_ONLY_NO_NATIVE_PARENT_OR_GRT_CLAIM', boxes=bx, box_count=len(bx),
                collisions=coll, outside=outside,
                seams_um=dict(vm_collective=round(co[0] - (vm[0] + vm[2]), 3), collective_hc_s=round(hc[0] - (co[0] + co[2]), 3),
                              capture_gather=round(ga[1] - (ca[1] + ca[3]), 3),
                              s14w=round(min(lay['mix4_slot'][0], b['sp_sseq'][0]) - can['wide_hub']['hub_x_um'][0], 3),
                              s14e=round(can['wide_hub']['hub_x_um'][1] - max(v[0] + v[2] for k, v in b.items() if k.startswith('sp_')), 3)),
                hub_x_um=can['wide_hub']['hub_x_um'], hub_width_um=can['wide_hub']['hub_width_um'],
                source_sha256={str(layout_path): hashlib.sha256(rel(layout_path).read_bytes()).hexdigest(),
                               str(canonical_path): hashlib.sha256(rel(canonical_path).read_bytes()).hexdigest()})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--layout', action='append', required=True, help='hub layout JSON (repeatable)')
    ap.add_argument('--canonical', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    rep = {Path(p).stem: audit(p, a.canonical) for p in a.layout}
    a.out.write_text(json.dumps(rep, indent=1) + '\n')
    bad = {k: (v['collisions'], v['outside']) for k, v in rep.items() if v['collisions'] or v['outside']}
    print(json.dumps({k: dict(boxes=v['box_count'], collisions=len(v['collisions']), outside=len(v['outside']), seams=v['seams_um'])
                      for k, v in rep.items()}))
    raise SystemExit(1 if bad else 0)


if __name__ == '__main__':
    main()
