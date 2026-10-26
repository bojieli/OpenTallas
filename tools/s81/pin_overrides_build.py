#!/usr/bin/env python3
"""Build the generator's --pin-overrides file (opentallas.s81.pin_overrides.v1) from GEO-S search results.

Each --cand ID=PATH[:adopt] names one GEO-S result (tools/s81/hub_face_repin_search.py `port_shifts_um` per inst, or
tools/s81/die_link_repin_search.py `port_shifts_master_frame_um` per master).  Only ':adopt' candidates are applied by
the generator; the others are carried for the record.  The file is bound by sha256 in the GEN source manifest.

  python3 tools/s81/pin_overrides_build.py --out results/physical/die_iter_1012/s81/gen18_pin_overrides.json \
      --cand C1=results/arch/.../C1_hc_tower_slice_permutation.json:adopt --cand C2=...:adopt
"""
import argparse
import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--cand', action='append', default=[], help='ID=PATH[:adopt]')
    ap.add_argument('--note', default='')
    a = ap.parse_args()
    cands = []
    for c in a.cand:
        cid, rest = c.split('=', 1)
        adopt = rest.endswith(':adopt')
        path = rest[:-len(':adopt')] if adopt else rest
        p = Path(path) if Path(path).is_absolute() else R / path
        d = json.loads(p.read_text())
        pins = []
        for e in d.get('port_shifts_um', []):
            pins.append(dict(inst=e['inst'], port=e['port'], shift_um=e['shift_um']))
        for e in d.get('port_shifts_master_frame_um', []):
            pins.append(dict(master=e['master'], port=e['port'], shift_um=e['shift_um']))
        for e in d.get('port_placements_um', []):        # absolute form, if a candidate provides it
            pins.append({k: e[k] for k in ('inst', 'master', 'port', 'face', 'coord_um') if k in e})
        assert pins, (cid, path, 'no pin moves in candidate')
        cands.append(dict(id=cid, adopted=adopt, source=str(path), source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                          measured_on=d.get('source_sha256'), scope=d.get('scope'), totals=d.get('totals'), pins=pins))
    out = dict(schema='opentallas.s81.pin_overrides.v1', tool='tools/s81/pin_overrides_build.py', note=a.note,
               candidates=cands)
    o = Path(a.out) if Path(a.out).is_absolute() else R / a.out
    o.parent.mkdir(parents=True, exist_ok=True)
    o.write_text(json.dumps(out, indent=1) + '\n')
    print(a.out, [(c['id'], c['adopted'], len(c['pins'])) for c in cands])


if __name__ == '__main__':
    main()
