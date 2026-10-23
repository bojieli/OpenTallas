#!/usr/bin/env python3
"""Measure a pre-tree profile from the actual selected, flattened source pair.

Preparation only reads source. Execute generated run.sh on the fleet. Unknown
instances/parameter expressions fail; there is no revision-wide age fallback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def selected_instance(text, prefix, parent_params):
    found = []
    for m in re.finditer(r'\b(' + prefix + r'\w*)\s*#\s*\(', text):
        depth = 1
        pos = m.end()
        end = pos
        while depth:
            assert end < len(text), 'unterminated parameter list'
            depth += (text[end] == '(') - (text[end] == ')')
            end += 1
        tail = re.match(r'\s+(u_pt\w*)\s*\(', text[end:])
        if not tail:
            continue
        params = text[pos:end-1]
        for key, value in parent_params.items():
            if type(value) is int:
                params = re.sub(r'(?<![.\w])' + re.escape(key) + r'\b', str(value), params)
        # Parameter identifiers after '.' are names; remaining identifiers must
        # have been bound by the actual parent contract, never guessed.
        values = re.sub(r'\.[A-Za-z_]\w*\s*\(', '(', params)
        assert not re.search(r'[A-Za-z_]', values), ('unbound selected parameter', params)
        found.append((m.group(1), params))
    assert len(set(found)) == 1, ('ambiguous or missing selected pre-tree', found)
    return found[0]


def prepare(a):
    c = json.loads(a.contract.read_text())
    inst = c['instances']
    records = {}
    selected = {}
    base = inst['su_SW0']
    for g in range(1, 4):
        other = inst[f'su_SW{g}']
        assert other['master'] == base['master'], 'different selected slice masters need separate profiles'
        omit = {'G', 'QID'}
        assert {k:v for k,v in other['params'].items() if k not in omit} == {k:v for k,v in base['params'].items() if k not in omit}, 'different slice timing parameters need separate profiles'
    a.out.mkdir(parents=True, exist_ok=True)
    for role, name, prefix in [('slice', 'su_SW0', 'ot_hbm_su_red_pretree_s'),
                               ('join', 'sucore_SW', 'ot_hbm_su_red_pretree_j')]:
        parent = inst[name]
        assert parent['params'].get('PRETREE') == 1
        assert parent['params'].get('MUT', 0) == 0
        path = a.bundle / 'masters' / (parent['master'] + '.sv')
        data = path.read_bytes()
        module, params = selected_instance(data.decode(), prefix, parent['params'])
        target = a.out / (role + '.sv')
        target.write_bytes(data)
        selected[role] = (module, params)
        records[role] = dict(path=str(target.resolve()), module=module,
                             sha256=hashlib.sha256(data).hexdigest(),
                             actual_parent=name, master=parent['master'],
                             parent_params=parent['params'], instantiation_params=params)
    # The qcore's command enters e_v before the pre-tree operand is selected.
    # Fail on an unknown command interface rather than inheriting this edge.
    join_text = (a.out/'join.sv').read_text()
    assert re.search(r'else\s+e_v\s*<=\s*red_cmd\[73\]', join_text), 'unknown command-to-operand source; measure it separately'
    tb = a.template.read_text()
    tb = tb.replace('ot_hbm_su_red_pretree_s_m72 #(.LAT(6))', selected['slice'][0] + ' #(' + selected['slice'][1] + ')')
    tb = tb.replace('ot_hbm_su_red_pretree_j_r13_m73 #(.LAT(6))', selected['join'][0] + ' #(' + selected['join'][1] + ')')
    assert 'ot_hbm_su_red_pretree_s_m72' not in tb or selected['slice'][0] == 'ot_hbm_su_red_pretree_s_m72'
    assert 'ot_hbm_su_red_pretree_j_r13_m73' not in tb or selected['join'][0] == 'ot_hbm_su_red_pretree_j_r13_m73'
    (a.out/'pt_latency.sv').write_text(tb)
    (a.out/'selected.json').write_text(json.dumps(dict(
        contract_sha256=hashlib.sha256(a.contract.read_bytes()).hexdigest(),
        sources=records), indent=1) + '\n')
    script = Path(__file__).resolve()
    (a.out/'finalize_profile.py').write_text(script.read_text())
    (a.out/'run.sh').write_text('''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing --top-module tb -j 2 -Wno-fatal -Wno-PINMISSING -Mdir obj pt_latency.sv slice.sv join.sv > build.log 2>&1
./obj/Vtb | tee measure.log
python3 finalize_profile.py --finalize .
''')
    print('PRETREE_PROFILE_PREPARED', json.dumps(selected))


def finalize(root):
    root = root.resolve()
    text = (root/'measure.log').read_text()
    edges = {}
    for role in ('INPUT', 'SLICE', 'JOIN'):
        v = re.findall(r'PT_LAT ' + role + r' edge=(\d+)', text)
        assert len(v) == 1, (role, v)
        edges[role] = int(v[0])
    assert re.search(r'PT_LAT JOIN .*x=3f800000 max=0 fault=0/0000', text), 'numerical/fault witness failed'
    selected = json.loads((root/'selected.json').read_text())
    for role, source in selected['sources'].items():
        path = root/(role+'.sv')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
        source['path'] = role + '.sv'
    age = edges['JOIN']-edges['INPUT']-1
    assert age > 0
    receipt = dict(schema='opentallas.hbm.pretree-timing.v1',
                   input_sample_edge=edges['INPUT'], slice_sample_edge=edges['SLICE'],
                   join_sample_edge=edges['JOIN'], red_command_to_operand_sample=1,
                   tree_to_reducer=age, sources=selected['sources'],
                   contract_sha256=selected['contract_sha256'],
                   scope='selected source functional profile; no physical timing claim')
    (root/'pretree_profile.json').write_text(json.dumps(receipt, indent=1)+'\n')
    print('PRETREE_PROFILE_MEASURED', age)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract', type=Path)
    p.add_argument('--bundle', type=Path)
    p.add_argument('--template', type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--finalize', type=Path)
    a = p.parse_args()
    if a.finalize:
        finalize(a.finalize)
    else:
        assert all((a.contract, a.bundle, a.template, a.out))
        prepare(a)


if __name__ == '__main__':
    main()
