"""Exact, source-bound hard-clock feedthroughs to declared output ports."""
import re
from pathlib import Path
from raw_macro_clocks import groups

PORT = re.compile(r'[A-Za-z_]\w*(?:\[\d+\])?')
NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_.$\[\]/]*')


def contract(spec, root=None):
    rows = spec.get('forwarded_clock_outputs', [])
    if not isinstance(rows, list):
        raise ValueError('forwarded clock outputs require a list')
    soft = {r['port']: r for r in spec.get('forwarded_soft_clocks', [])}
    children = {c.get('inst'): c for c in spec.get('children', [])}
    seen = set(); result = []
    for row in rows:
        keys = {'input', 'output', 'inst', 'master', 'input_pin', 'output_pin'}
        if (not isinstance(row, dict) or set(row) != keys or
                any(not isinstance(v, str) or not (PORT if k in ('input','output') else NAME).fullmatch(v)
                    for k, v in row.items())):
            raise ValueError('forwarded clock output needs exact input/output/instance/master/clock-pin pair')
        ip, op = row['input'], row['output']
        child = children.get(row['inst'])
        domain = soft.get(ip, {}).get('domain')
        outputs = (spec.get('clock_entry_domains', {}).get(domain) or {}).get('outputs', [])
        if (ip not in soft or op == ip or op in seen or op.split('[')[0] not in outputs or
                child is None or Path(child['view']).name != row['master'] or child.get('count', 1) != 1):
            raise ValueError('forwarded clock output missing exact domain/child or duplicate output')
        if row['input_pin'] == row['output_pin']:
            raise ValueError('forwarded clock output pin pair must be distinct')
        if root is not None:
            for corner in ('tt','ff','ss'):
                lib = Path(root) / child['view'] / f'{row["master"]}_{corner}.lib'
                library = list(groups(lib.read_text()))
                cells = [(n,b) for k,n,b in groups(library[0][2]) if k == 'cell'] if len(library)==1 else []
                if len(cells)!=1 or cells[0][0] != row['master']:
                    raise ValueError('forwarded clock output actual Liberty master mismatch')
                pins = {n:b for k,n,b in groups(cells[0][1]) if k == 'pin'}
                inp, out = pins.get(row['input_pin'], ''), pins.get(row['output_pin'], '')
                if not re.search(r'\bclock\s*:\s*true\s*;', inp) or not re.search(r'\bdirection\s*:\s*input\s*;', inp):
                    raise ValueError('forwarded clock output source is not an actual Liberty clock input')
                arcs = [b for k,_,b in groups(out) if k == 'timing']
                if (not re.search(r'\bdirection\s*:\s*output\s*;', out) or len(arcs)!=1 or
                        not re.search(r'\brelated_pin\s*:\s*"?'+re.escape(row['input_pin'])+r'"?\s*;', arcs[0]) or
                        not re.search(r'\btiming_type\s*:\s*combinational\s*;', arcs[0]) or
                        not re.search(r'\btiming_sense\s*:\s*positive_unate\s*;', arcs[0]) or
                        re.search(r'\bwhen\s*:', arcs[0])):
                    raise ValueError('forwarded clock output requires one unconditional positive clock-through Liberty arc')
        seen.add(op); result.append(dict(row))
    return result


def metadata(spec, root=None):
    rows = contract(spec, root)
    if not rows:
        return ''
    return 'set ::ot_ce_fwd_outputs [dict create ' + ' '.join(
        '{'+r['output']+'} {'+' '.join(k+' {'+r[k]+'}' for k in ('input','inst','master','input_pin','output_pin'))+'}'
        for r in rows) + ']\n'
