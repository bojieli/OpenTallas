#!/usr/bin/env python3
"""Explicit sixteen-instance CP51.84 grants, preserving actual clear GEN2e homes.

Read a completed GEN manifest. Each new slot lies inside its previous CP60.48
footprint and clears every other real placed block by21.6um. The registered
relative master's exact kit face plan is mandatory, never the old SVG alias.
This grants CP only; relative SVG/XC still need their own physical qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hbm_die_v16/d4g_layers'))
import l15_smb_relative as L

CP = L.CP
WH = 51.84
CLR = 21.6
GRANT = 'd4g_gen2e_smbcp_relative_1019'


def rect(p):
    return p['x'], p['y'], p['x'] + p['w'], p['y'] + p['h']


def gap(a, b):
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3])


def apply(g, contract, manifest, manifest_hash=''):
    ports = L.rtl_ports()[CP]
    faces = {p: ('N' if p == 'cfg_data' else 'S' if p == 'a_data' else 'E' if p == 'b_data' else 'W') for p in ports}
    counts = {f: sum(ports[p]['bits'] for p in ports if faces[p] == f) for f in 'NSEW'}
    if sum(counts.values()) != 895 or max(counts.values()) / WH > 6:
        raise ValueError(f'CP face map differs from qualified895pin PBkit: {counts}')
    names = sorted(n for n, v in contract['instances'].items() if n.startswith('cp_svg_'))
    if len(names) != 16:
        raise ValueError(f'expected16CP instances, got{len(names)}')
    PL = manifest['placement']
    occupied = [(n, rect(p)) for n, p in PL.items() if n not in names]
    choices, minima = {}, {}
    for n in names:
        v = contract['instances'][n]
        if v['master'] != CP or v['slot'] != n or v['ports'] != ports or v['params'] != L.PARAMS[CP]:
            raise ValueError(f'{n}: CP relative contract is absent or partially migrated')
        old = PL[n]
        if old['w'] < WH or old['h'] < WH:
            raise ValueError(f'{n}: prior home too small')
        xs = [i * (old['w'] - WH) / 4 for i in range(5)]
        ys = [i * (old['h'] - WH) / 4 for i in range(5)]
        candidates = []
        for dx in xs:
            for dy in ys:
                x = round(round((old['x'] + dx) / .216) * .216, 3)
                y = round(round((old['y'] + dy) / .216) * .216, 3)
                r = x, y, x + WH, y + WH
                if r[0] < old['x'] - .001 or r[1] < old['y'] - .001 or r[2] > old['x'] + old['w'] + .001 or r[3] > old['y'] + old['h'] + .001:
                    continue
                md, peer = min((gap(r, other), peer) for peer, other in occupied)
                if md >= CLR - .001:
                    centre_move = abs(x + WH/2 - old['x'] - old['w']/2) + abs(y + WH/2 - old['y'] - old['h']/2)
                    candidates.append((centre_move, -md, x, y, peer))
        if not candidates:
            raise ValueError(f'{n}: no clear51.84site within actual old home; re-plan instead of aliasing SVG')
        _, neg_md, x, y, peer = min(candidates)
        choices[n] = dict(x=x, y=y, w=WH, h=WH, orient=old['o'], old=dict(old))
        minima[n] = dict(clearance_um=round(-neg_md, 3), nearest=peer)
        occupied.append((n, (x, y, x+WH, y+WH)))
    slots = {s['name']: s for s in g['slots']}
    for n, p in choices.items():
        slot = dict(name=n, instance=n, cell=CP, kind='tile', parent='die', outline=dict(w=WH, h=WH),
            origin=dict(x=p['x'], y=p['y'], orient=p['orient']), pins=[], pin_status='FACES_ONLY',
            grant=GRANT, layer_cap='M5', signal_max_layer='M5', pg_layer='M5', strap_layer='M6',
            synth_pin_bind=dict(source='hdie_cp_svg_rel_pb_1019 kit/receipt703670eac; source ot_static_run_target; exact895ports',
                                faces=faces, windows=[]),
            notes='L15 actual CP instance home; no SVG alias.51.84square PBkit, measuredpin-bound util19.8%; resetsettle+2; cfg/run+2 unchanged. SVG/XC physicaladoption open.')
        if n in slots:
            g['slots'][g['slots'].index(slots[n])] = slot
        else:
            g['slots'].append(slot)
    rep = dict(schema='opentallas.hbm.smbcp_grants.v1', grant=GRANT, source_manifest_sha256=manifest_hash,
        instances=choices, clearance=minima, minimum_clearance_um=min(x['clearance_um'] for x in minima.values()),
        faces=faces, face_bits=counts, pin_density_max=max(counts.values())/WH,
        total_CP_slot_um2=16*WH*WH, no_svg_alias=True, violations=[],
        qualification='CP grant only; relative SVG/XC native hardening+router IDs still open')
    return g, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract', required=True); ap.add_argument('--manifest', required=True)
    ap.add_argument('--grants', required=True); ap.add_argument('--out', required=True); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    try:
        mpath = Path(a.manifest)
        g, rep = apply(L.load(a.grants), L.load(a.contract), L.load(a.manifest), hashlib.sha256(mpath.read_bytes()).hexdigest())
    except (ValueError, KeyError) as e:
        Path(a.report).write_text(json.dumps(dict(violations=[str(e)]), indent=1)+'\n')
        print('SMBCP_GRANT_FAIL', e); return 1
    Path(a.out).write_text(json.dumps(g, indent=1)+'\n')
    Path(a.report).write_text(json.dumps(rep, indent=1)+'\n')
    print('SMBCP_GRANT_OK16', '51.84square895pins', 'minclear', rep['minimum_clearance_um'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
