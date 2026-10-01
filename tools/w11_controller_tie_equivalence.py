#!/usr/bin/env python3
"""Compare full mapped graphs after collapsing only verified ASAP7 constant ties."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

TIES = {'TIEHIx1_ASAP7_75t_R': ('H', '1'), 'TIELOx1_ASAP7_75t_R': ('L', '0')}

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()

def prove(before, after, top, sequential_types):
    assert set(before['modules']) == set(after['modules']), 'module set changed'
    a, b = before['modules'][top], after['modules'][top]
    for name in before['modules']:
        if name != top:
            assert before['modules'][name] == after['modules'][name], ('library module changed', name)
    added = set(b['cells']) - set(a['cells'])
    assert not (set(a['cells']) - set(b['cells'])), 'original cells removed'
    constants, tie_counts = {}, Counter()
    for name in added:
        cell = b['cells'][name]
        assert cell['type'] in TIES, ('non-tie addition', name)
        port, value = TIES[cell['type']]
        assert not cell['parameters'], ('tie parameters changed', name)
        assert set(cell['connections']) == {port}, ('unexpected tie connection', name)
        bits = cell['connections'][port]
        assert len(bits) == 1 and isinstance(bits[0], int), 'invalid tie output'
        assert bits[0] not in constants, 'multiple constant drivers'
        constants[bits[0]] = value
        tie_counts[cell['type']] += 1
    assert added, 'no constant ties materialized'
    def collapse(bit):
        return constants.get(bit, bit)
    assert set(a['ports']) == set(b['ports']), 'module ports changed'
    assert not (set(a['netnames']) - set(b['netnames'])), 'original named nets removed'
    old_to_new, new_to_old = {}, {}
    def bind(old, new):
        assert len(old) == len(new), 'net width changed'
        for x, y in zip(old, new):
            y = collapse(y)
            if isinstance(x, str):
                assert x == y, ('constant changed', x, y)
            else:
                assert isinstance(y, int), ('signal replaced by constant', x, y)
                assert old_to_new.setdefault(x, y) == y, 'alias split'
                assert new_to_old.setdefault(y, x) == x, 'signals merged'
    for name, net in a['netnames'].items():
        other = b['netnames'][name]
        assert {k:v for k,v in net.items() if k != 'bits'} == {k:v for k,v in other.items() if k != 'bits'}, ('net metadata changed', name)
        bind(net['bits'], other['bits'])
    for name, port in a['ports'].items():
        other = b['ports'][name]
        assert {k:v for k,v in port.items() if k != 'bits'} == {k:v for k,v in other.items() if k != 'bits'}, ('port metadata changed', name)
        bind(port['bits'], other['bits'])
    def canonical(bits):
        return [new_to_old[collapse(x)] if isinstance(collapse(x), int) else collapse(x) for x in bits]
    def cell_equal(original, changed):
        if {k:v for k,v in original.items() if k != 'connections'} != {k:v for k,v in changed.items() if k != 'connections'}:
            return False
        return set(original['connections']) == set(changed['connections']) and all(original['connections'][p] == canonical(changed['connections'][p]) for p in original['connections'])
    connection_count = 0
    for name, cell in a['cells'].items():
        assert cell_equal(cell, b['cells'][name]), ('cell type/parameters/ports changed', name)
        connection_count += len(cell['connections'])
    counts = Counter(c['type'] for c in a['cells'].values())
    seq = sum(n for typ,n in counts.items() if typ in sequential_types)
    assert seq == 337084, ('full sequential count changed', seq)
    assert sum(c['type'] in sequential_types for c in b['cells'].values()) == seq
    assert seq >= 270418
    # Fault injection uses one existing cell; it never changes the measured graphs.
    name = next(n for n,c in a['cells'].items() if c['connections'])
    original, actual = a['cells'][name], b['cells'][name]
    mutants = []
    for kind in ['type','parameter','port']:
        mutant = dict(actual)
        if kind == 'type': mutant['type'] = '__wrong_cell_type'
        elif kind == 'parameter': mutant['parameters'] = {**actual['parameters'], '__wrong_parameter':'1'}
        else:
            mutant['connections'] = {p:list(bits) for p,bits in actual['connections'].items()}
            p = next(iter(mutant['connections']))
            mutant['connections'][p][0] = '0' if canonical(mutant['connections'][p])[0] != '0' else '1'
        assert not cell_equal(original, mutant), ('mutant accepted', kind)
        mutants.append(kind)
    return {'verdict':'PASS', 'original_cells':len(a['cells']), 'transformed_cells':len(b['cells']), 'every_original_cell_and_type_parameters_ports_equal':True, 'cell_port_connections_compared':connection_count, 'original_named_nets_compared':len(a['netnames']), 'top_ports_compared':len(a['ports']), 'original_type_counts':dict(sorted(counts.items())), 'added_tie_counts':dict(sorted(tie_counts.items())), 'added_tie_count':len(added), 'added_tie_area_um2':len(added)*0.04374, 'sequential_before':seq, 'sequential_after':seq, 'guard_expected':338023, 'guard_minimum':270418, 'fault_injection_rejected':mutants}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--work', type=Path, required=True); ap.add_argument('--lib-dir',type=Path,required=True); args=ap.parse_args()
    seq=set(); library_pins={}
    for p in sorted(args.lib_dir.glob('*RVT_TT*lib')):
        text=p.read_text();library_pins[str(p)]=digest(p)
        starts=list(re.finditer(r'\bcell\s*\(\s*([^)]*)\)',text))
        for i,m in enumerate(starts):
            end=starts[i+1].start() if i+1<len(starts) else len(text)
            if re.search(r'\b(?:ff|latch)\s*\(',text[m.end():end]): seq.add(m[1].strip().strip('"'))
    before=json.loads((args.work/'before.json').read_text());after=json.loads((args.work/'after.json').read_text())
    result=prove(before,after,'ot_v41_attn_eng_ctl_phys',seq)
    result['input_sha256']={n:digest(args.work/n) for n in ['original.v','before.json','after.json','tied.v','transform.ys','transform.log']}
    result['library_sha256']=library_pins;result['checker_sha256']=digest(__file__);result['physical_run_launched']=False;result['arithmetic_or_timing_optimization_run']=False
    (args.work/'proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['original_type_counts','library_sha256','input_sha256']}))
if __name__ == '__main__': main()
