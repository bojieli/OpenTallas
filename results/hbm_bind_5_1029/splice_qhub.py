#!/usr/bin/env python3
"""HBM-BIND-5: expose the hub HC qhub interior in the HBM-BIND-4 b1 netlist without re-elaborating the die.

A re-elaboration with ot_hbm_hc_qhub_static/qcen dissolved renumbers Yosys primitives die-wide (name rebase by sort
order then fails on the native128 capture splits).  Instead: take the b1 normalized Yosys JSON unchanged and replace
ONLY the blackbox type of the top cells hc_NE / hc_NW by the elaborated W128 qhub body ($paramod ... qhub + qcen and
the leaf stubs they reference) from the e2 elaboration of the same sources (rtl/.../static_hc, preferred).  Checks
(fail closed): the donor top cell has the same type, identical port names/widths/directions and identical
connections bit-for-bit (up to the module-local bit numbering of the two top modules, mapped through the base cell's
own connections); every copied module name is new to the base or has an identical port signature; the base top's
other cells, nets and every other module are byte-identical.  No logic, cycle or constant change.
usage: splice_qhub.py BASE.json DONOR.json OUT.json RECEIPT.json [--inst hc_NE --inst hc_NW]
"""
import argparse, copy, hashlib, json
from pathlib import Path
ap = argparse.ArgumentParser()
for x in ('base', 'donor', 'out', 'receipt'):
    ap.add_argument(x, type=Path)
ap.add_argument('--inst', action='append', default=None)
ap.add_argument('--top', default='hbm_current_native_top')
a = ap.parse_args()
insts = a.inst or ['hc_NE', 'hc_NW']
B = json.loads(a.base.read_text()); D = json.loads(a.donor.read_text())
bt, dt = B['modules'][a.top], D['modules'][a.top]
before = {k: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest() for k, v in B['modules'].items()}
def sig(m):
    return {p: (v['direction'], len(v['bits'])) for p, v in m.get('ports', {}).items()}
copied, types = set(), set()
for inst in insts:
    bc, dc = bt['cells'][inst], dt['cells'][inst]
    assert 'blackbox' in B['modules'][bc['type']].get('attributes', {}), (inst, 'base cell is not a blackbox leaf')
    dtyp = dc['type']; dm = D['modules'][dtyp]
    assert 'blackbox' not in dm.get('attributes', {}) and dm.get('cells'), (inst, 'donor body missing')
    assert dm.get('attributes', {}).get('hdlname', dtyp).endswith('ot_hbm_hc_qhub_static') or dtyp.endswith('\\ot_hbm_hc_qhub_static')
    # the base blackbox stub keeps default-parameter widths; the instance connections carry the W=128 widths
    bdir = {p: v['direction'] for p, v in B['modules'][bc['type']]['ports'].items()}
    assert {p: (bdir[p], len(bs)) for p, bs in bc['connections'].items()} == sig(dm), (inst, 'port signature differs')
    assert set(bc['connections']) == set(dc['connections']), inst
    # base and donor top bits are module-local; the instance connections must agree bit-for-bit under one map
    m = {}
    for p in bc['connections']:
        xs, ys = bc['connections'][p], dc['connections'][p]
        assert len(xs) == len(ys), (inst, p)
        for x, y in zip(xs, ys):
            if isinstance(x, str) or isinstance(y, str):
                assert x == y, (inst, p, 'constant differs', x, y)
            else:
                assert m.setdefault(y, x) == x, (inst, p, 'donor bit maps to two base bits')
    # parameters: base carries them on the cell, donor specialised them into the $paramod name
    for k, v in bc.get('parameters', {}).items():
        dv = dm.get('parameter_default_values', {}).get(k)
        assert dv is not None and int(dv, 2) == int(v, 2), (inst, 'parameter differs', k, v, dv)
    types.add(dtyp)
    bc['type'] = dtyp
    bc['parameters'] = {}
todo = list(types)
while todo:
    t = todo.pop()
    if t in copied:
        continue
    dm = D['modules'][t]
    if t in B['modules'] and t not in types:
        assert sig(B['modules'][t]) == sig(dm), (t, 'existing module signature differs')
        assert ('blackbox' in B['modules'][t].get('attributes', {})) == ('blackbox' in dm.get('attributes', {})), t
        continue
    assert t not in B['modules'], (t, 'name clash')
    B['modules'][t] = copy.deepcopy(dm); copied.add(t)
    for c in dm.get('cells', {}).values():
        if c['type'] in D['modules']:
            todo.append(c['type'])
after = {k: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest() for k, v in B['modules'].items()}
changed = sorted(k for k in before if before[k] != after[k])
assert changed == [a.top], changed
other = {k: v for k, v in bt['cells'].items() if k not in insts}
od = json.loads(a.base.read_text())['modules'][a.top]
assert all(od['cells'][k] == v for k, v in other.items()) and od['netnames'] == bt['netnames'] and od['ports'] == bt['ports']
a.out.write_text(json.dumps(B))
rec = dict(schema='hbm.bind5.splice_qhub.v1', base=str(a.base), donor=str(a.donor), instances=insts,
           new_type=sorted(types), copied_modules=sorted(copied), top_cells_changed=insts,
           other_top_cells_identical=len(other), other_modules_identical=len(before) - 1)
a.receipt.write_text(json.dumps(rec, indent=1)); print(json.dumps(rec))
