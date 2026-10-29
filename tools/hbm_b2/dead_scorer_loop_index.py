#!/usr/bin/env python3
"""Remove only proved-unused scorer for-loop index latch artifacts from proc JSON.

This source-preparation transform preserves every retained terminal. It rejects
latches with any load, module-port export, or explicit keep/dont_touch, and does
not add latch support or change RTL storage. Original JSON is never overwritten.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'die_plan'))

class Refused(ValueError):
    pass

def truth(value):
    return str(value).lower().strip('0') not in ('', 'false', 'none')

def prepare(data):
    result = dict(data)
    result['modules'] = dict(data['modules'])
    records = []
    for name, module in data['modules'].items():
        hdlname = str(module.get('attributes', {}).get('hdlname', ''))
        if hdlname != 'ot_hbm_idx_score_quarter_static_h':
            continue
        candidates = [(n, c) for n, c in module.get('cells', {}).items() if c['type'] == '$adlatch']
        if not candidates:
            continue
        if sorted(len(c['connections']['Q']) for _, c in candidates) != [1, 2, 29]:
            raise Refused('unexpected scorer latch shape')
        deleted = []
        for cellname, cell in candidates:
            outputs = set(cell['connections']['Q'])
            aliases = [(n, v) for n, v in module['netnames'].items() if outputs.intersection(v['bits'])]
            if not aliases or any(not n.endswith('.j') or '$fordecl_block$' not in n for n, _ in aliases):
                raise Refused(f'{name}/{cellname}: not exclusively a for-loop j temporary')
            attributes = [cell.get('attributes', {})] + [v.get('attributes', {}) for _, v in aliases]
            if any(truth(a.get(k, 0)) for a in attributes for k in ('keep', 'dont_touch', 'donttouch')):
                raise Refused(f'{name}/{cellname}: explicitly retained')
            exports = [p for p, port in module.get('ports', {}).items() if outputs.intersection(port['bits'])]
            loads = [(n, p) for n, c in module['cells'].items() for p, bs in c['connections'].items()
                     if c['port_directions'].get(p) in ('input', 'inout') and outputs.intersection(bs)]
            if exports or loads:
                raise Refused(f'{name}/{cellname}: observable Q exports={exports} loads={loads[:3]}')
            deleted.append(cellname)
            records.append(dict(module=name, cell=cellname, type=cell['type'], width=len(outputs),
                                aliases=[n for n, _ in aliases], loads=0, module_ports=0, keep=False,
                                source=cell.get('attributes', {}).get('src')))
        updated = dict(module)
        updated['cells'] = {n: c for n, c in module['cells'].items() if n not in deleted}
        result['modules'][name] = updated
    if len(records) != 3:
        raise Refused(f'expected exactly three scorer module latch artifacts, got {len(records)}')
    return result, records

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.out.resolve():
        raise Refused('original source JSON must remain immutable')
    original = json.loads(args.source.read_text())
    prepared, records = prepare(original)
    # A Q declared on ANY module port must prevent this transform, even when
    # there is no internal cell load. This controls the production criterion.
    mutant = dict(original)
    mutant['modules'] = dict(original['modules'])
    name = records[0]['module']
    changed = dict(original['modules'][name])
    changed['ports'] = dict(changed.get('ports', {}))
    q = changed['cells'][records[0]['cell']]['connections']['Q']
    changed['ports']['__mutant_observable_loop_index'] = dict(direction='output', bits=q)
    mutant['modules'][name] = changed
    try:
        prepare(mutant)
    except Refused as error:
        if 'observable Q' not in str(error):
            raise
        control = str(error)
    else:
        raise Refused('observable-Q mutant was accepted')
    import bind_elab as E
    before = E.flatten(original, 'hbm_current_native_top')
    after = E.flatten(prepared, 'hbm_current_native_top')
    deleted_flat = [c.path for c in before.cells if c.ytype == '$adlatch']
    if len(deleted_flat) != 12 or any(c.ytype == '$adlatch' for c in after.cells):
        raise Refused('unexpected flat latch inventory')
    retained_before = {c.path: c for c in before.cells if c.ytype != '$adlatch'}
    retained_after = {c.path: c for c in after.cells}
    if retained_before.keys() != retained_after.keys() or before.top_ports != after.top_ports:
        raise Refused('retained cells or top ports changed')
    for path, old in retained_before.items():
        new = retained_after[path]
        if any(getattr(old, k) != getattr(new, k) for k in ('module', 'params', 'ports', 'dirs', 'kind', 'ytype', 'yparams')):
            raise Refused(f'retained terminal changed: {path}')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(prepared, separators=(',', ':')))
    receipt = dict(schema='hbm.dead_loop_index_source_prep.v1', verdict='PASS', module_cells=records,
                   deleted_flat_cells=deleted_flat, retained_cells=len(retained_after),
                   every_retained_terminal_identical=True, every_module_port_checked=True,
                   observable_q_mutant='CAUGHT', mutant_reason=control, source=str(args.source),
                   output=str(args.out), added_cycles=0)
    args.receipt.write_text(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps(dict(verdict='PASS', deleted_flat=len(deleted_flat), retained=len(retained_after),
                         observable_q_mutant='CAUGHT', added_cycles=0)))

if __name__ == '__main__':
    main()
