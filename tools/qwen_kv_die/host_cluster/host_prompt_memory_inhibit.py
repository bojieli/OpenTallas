#!/usr/bin/env python3
"""PRIVATE new reset contract: inhibit all seven macro reads/writes at raw por.

This changes reference AND candidate reset behavior. It is not equivalence to
the previous assertion behavior and is not admitted by the plain-reset API.
"""
from pathlib import Path
import hashlib
import json
import re

TOP = 'qkd_hr_core_prompt_mu4p2_n32'
ROOT = 'u_rank__u_control__por_n'
record = json.loads(Path(TOP + '.json').read_text())
assert len(record['macros']) == 7
manifest = {'scope': 'PRIVATE new raw-por memory-access inhibit contract; NOT plain reset admission',
            'root': ROOT, 'active_level': 0, 'added_released_datapath_cycles': 0,
            'reference_and_candidate_changed': True, 'macro_ports': []}

def transform(text, candidate):
    decl = []
    for index, row in enumerate(record['macros']):
        one_rw = row['type'].startswith('ot_sram_1rw_')
        pins = ['ce_in'] if one_rw else ['r_ce_in', 'w_ce_in']
        name = row['instance'].split('.')[0] if candidate else '\\' + row['original']
        pattern = r'(\b\w+\s+' + re.escape(name) + r'\s*\()(.*?)(\);)'
        matches = list(re.finditer(pattern, text, re.S))
        assert len(matches) == 1, (name, len(matches))
        match = matches[0]
        ports = match.group(2)
        for pin in pins:
            p = re.compile(r'(\.' + pin + r'\s*\()([^()]+)(\))')
            found = list(p.finditer(ports))
            assert len(found) == 1, (name, pin)
            old = found[0].group(2).strip()
            net = f'raw_por_mem_{index}_{pin}'
            cell = f'u_raw_por_mem_{index}_{pin}'
            ports = p.sub(lambda m: m.group(1) + net + m.group(3), ports)
            decl += [f'wire {net};', f'(* keep *) AND2x2_ASAP7_75t_R {cell} (.A({ROOT}),.B({old} ),.Y({net}));']
            if candidate:
                manifest['macro_ports'].append(dict(index=index, macro=row['instance'], original=row['original'],
                    master=row['type'], pin=pin, gate=cell, original_expression=old,
                    read=one_rw or pin == 'r_ce_in', write=one_rw or pin == 'w_ce_in'))
        text = text[:match.start()] + match.group(1) + ports + match.group(3) + text[match.end():]
    end = text.index('\nendmodule')
    return text[:end] + '\n' + '\n'.join(decl) + '\n' + text[end:]

reference = Path('original.v').read_text()
reference = reference.replace('module ' + record['original_top'] + '(', 'module ' + record['original_top'] + '_guard(', 1)
candidate = Path(TOP + '.sv').read_text().replace('module ' + TOP + ' (', 'module ' + TOP + '_guard (', 1)
reference = transform(reference, False)
candidate = transform(candidate, True)
Path('guard_original.v').write_text(reference)
Path(TOP + '_guard.sv').write_text(candidate)
manifest.update(physical_gate_count=len(manifest['macro_ports']),
    read_paths=sum(r['read'] for r in manifest['macro_ports']),
    write_paths=sum(r['write'] for r in manifest['macro_ports']),
    proposed_root_loads=11,
    original_input_sha256=hashlib.sha256(Path('original.v').read_bytes()).hexdigest(),
    previous_candidate_sha256=hashlib.sha256(Path(TOP+'.sv').read_bytes()).hexdigest(),
    reference_sha256=hashlib.sha256(reference.encode()).hexdigest(),
    candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest())
assert (manifest['physical_gate_count'], manifest['read_paths'], manifest['write_paths']) == (10, 7, 7)
Path('guard_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
record.update(top=TOP+'_guard', original_top=record['original_top']+'_guard', source_sha256=manifest['reference_sha256'], generated_sha256=manifest['candidate_sha256'])
Path(TOP+'_guard.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k!='macro_ports'}),flush=True)
