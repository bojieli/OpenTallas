#!/usr/bin/env python3
"""Bind the exact first CLOSED QF view at its checked legal native phase."""
import argparse, hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / 'results/arch/s81_die72_1021/g9_assembly/qf_first_closed'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', required=True, type=Path)
    ap.add_argument('--table', required=True, type=Path)
    a = ap.parse_args()
    owner = json.loads((PACKET / 'owner_packet.json').read_text())
    proof = json.loads((PACKET / 'binding.json').read_text())
    for path, info in owner['files'].items():
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', info['ref'] + ':' + path])
        assert hashlib.sha256(raw).hexdigest() == info['sha256'], path
        if '/views/' in path:
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == info['sha256'], path
    plan = json.loads(a.plan.read_text())
    table = json.loads(a.table.read_text())
    blocks = [b for b in plan['blocks'] if b['name'] == 'iqf']
    assert len(blocks) == 1
    block = blocks[0]
    row = table['masters'][block['master']]
    assert row['module'] == owner['master'] and not row.get('view')
    assert not row.get('params') and owner['params'] == {}
    assert [block['x'], block['y']] == proof['old_origin_um']
    assert [block['w'], block['h']] == owner['outline_um']
    assert all(v['offtrack'] == 0 for v in proof['candidate_fullpins']['layers'].values())
    row.update(ref=owner['source'], view=proof['view'], view_ref=owner['record'], params={},
               view_note='Exact CLOSED QF MAIN native30; 3 pin-to-pin/2 reset edges unchanged; parent route/STA owed')
    path = 'rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv'
    refs = table.setdefault('rtl_refs', {}).setdefault(owner['source'], [])
    if path not in refs:
        refs.append(path)
    prefer = table.setdefault('prefer', [])
    selected = owner['source'] + '/' + path
    if selected not in prefer:
        prefer.append(selected)
    block['x'], block['y'] = proof['candidate_origin_um']
    for link in plan['links']:
        for ep in link['e']:
            if plan['blocks'][ep[0]]['name'] == 'iqf':
                ep[2] = round(ep[2] + proof['delta_nm'][0] / 1000, 4)
                ep[3] = round(ep[3] + proof['delta_nm'][1] / 1000, 4)
        for field in ('h', 'sp', 's', 'L', 'station_dirs'):
            link.pop(field, None)
    plan['facts']['qf_closed_binding'] = proof
    plan['facts']['physical72']['routing'] = 'INVALIDATED_BY_EXACT_QF_NATIVE_PHASE; fresh routing required'
    a.plan.write_text(json.dumps(plan, indent=1) + '\n')
    a.table.write_text(json.dumps(table, indent=1) + '\n')
    print('G9_QF_EXACT_CLOSED source/params/fullpins/bodyseal PASS; fresh paths/STA owed')


if __name__ == '__main__':
    main()
