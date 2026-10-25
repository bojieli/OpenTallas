#!/usr/bin/env python3
"""Extract a physical seam component retaining the partitions' actual RTL contracts.

The ordinary pair.py vehicle deliberately substitutes proof leaves. This helper
uses its geometric cut only, then restores the original contents, hard-core
hierarchy, sources and in-band epochs. It emits no route or STA command. G4
requires both native parent views to be SIGNED, with matching physical pins.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pair
import schema as S
from gen_phys import type_pins


def extract(raw, parts, plan_dir):
    if len(parts) != 2 or len(set(parts)) != 2:
        raise ValueError('exactly two distinct native partitions are required')
    parent = S.Plan(raw, Path(plan_dir) / 'die_plan.json')
    selected = {parent.parts[p]['type'] for p in parts}
    for tn in selected:
        if not parent.types[tn].get('contents'):
            raise ValueError(f'{tn}: no actual RTL contents')
        for c in parent.types[tn]['contents']:
            if c['module'].endswith('_proof_leaf') or 'proof leaf' in c.get('note', '').lower():
                raise ValueError(f'{tn}: proof RTL is not a native seam')
    cut, _unused_proof_rtl = pair.extract(raw, parts, 0, 'native_' + '_'.join(parts), cores=False,
                                         plan_dir=str(plan_dir))
    cut['partition_types'] = {tn: copy.deepcopy(parent.types[tn]) for tn in selected}
    for t in cut['partition_types'].values():
        for h in t.get('hard_cores', []):
            if h.get('pins_file') and not Path(h['pins_file']).is_absolute():
                h['pins_file'] = str((Path(plan_dir) / h['pins_file']).resolve())
    for q in cut['ports']:
        # Cutting an internal native connection to component IO must retain its
        # physical epoch wire. has_epoch() accepts this explicit override at IO.
        q['epoch'] = S.has_epoch(parent.ports[q['id']])
    cut['note'] = f'Native physical seam component {parts}: actual partition RTL preserved; no proof leaves'
    cut['census'] = {'none': 'Native two-part component; full target census and G5 remain on the parent die'}
    child = S.Plan(cut, Path(plan_dir) / 'native_pair_plan.json')
    for tn in selected:
        if sorted(type_pins(parent, tn)) != sorted(type_pins(child, tn)):
            raise ValueError(f'{tn}: native pin coordinates/order changed while cutting the pair: missing {list(set(type_pins(parent, tn))-set(type_pins(child, tn)))[:4]}, extra {list(set(type_pins(child, tn))-set(type_pins(parent, tn)))[:4]}')
    crossings = []
    for q in cut['ports']:
        if {q['src']['part'], q['dst']['part']} == set(parts):
            crossings.append(dict(id=q['id'], src=q['src'], dst=q['dst'], payload_bits=q['width'],
                                  physical_bits=S.port_pins_count(q), epoch=S.has_epoch(q),
                                  bit_layer_coordinate_um=child.port_pins(q['id'])))
    if not crossings:
        raise ValueError('the selected native partitions have no direct seam')
    contract = dict(kind='native-seam-preparation', parts=parts, actual_rtl_preserved=True,
                    native_parent_views_required=sorted(selected), route_or_sta_authorized=False,
                    blockers=['Actual native parent views must be SIGNED before assembled seam STA',
                              'Render and review the actual parent placements, seam clock and reset/start before routing'],
                    seam=crossings, inference_cycle_delta=0)
    return cut, contract


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan'); ap.add_argument('--parts', required=True); ap.add_argument('--out', required=True)
    a=ap.parse_args(); src=Path(a.plan).resolve(); out=Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cut, contract=extract(S.load(src), a.parts.split(','), src.parent)
    (out/'native_pair_plan.json').write_text(json.dumps(cut, indent=1)+'\n')
    (out/'native_seam_contract.json').write_text(json.dumps(contract, indent=1)+'\n')
    print(f'Native RTL retained; {len(contract["seam"])} physical crossings; no route/STA launched')

if __name__ == '__main__':
    main()
