#!/usr/bin/env python3
"""Audit HGI wrapper reachability; a port inventory alone never proves integration.

Contract rows name the elaborated engine source and wrapper instance/spec. Every
functional port must be mapped at full width to a real die net. The existing
wrapper generator independently enforces direction, tie classification, all
ports, and byte-for-byte wrapper regeneration. This adds HGI reachability:
classified constants/cfg shifts/folds are not accepted for functional HGI ports.
Run on a fleet host; imports use the selected checkout's actual generator.
"""
import argparse
import hashlib
import json
from pathlib import Path
import die_top_lint as L
import hbm_die_wrap as W

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(contract):
    errors, rows = [], []
    L.VARIANT = contract['variant']
    W.V._MODEL.clear()
    for block in contract['blocks']:
        row = dict(name=block['name'], owner=block['owner'], ports=[], errors=[])
        source = ROOT / block['source']
        if not source.exists():
            row['errors'].append('engine source not installed in this checkout')
        elif not block.get('source_sha256') or digest(source) != block['source_sha256']:
            row['errors'].append('engine source hash missing or mismatched')
        else:
            row['source_sha256'] = digest(source)
            ports = L.parse_module(block['source'], block['module'], block.get('params'))['ports']
            spec_path = ROOT / block.get('wrapper_spec', '__missing_wrapper_spec__')
            if not spec_path.exists():
                row['errors'].append('wrapper spec not installed: integration incomplete')
                row['ports'] = [dict(port=p, direction=d, bits=w, bind=None) for p, (d, w) in ports.items()]
            else:
                spec = json.loads(spec_path.read_text())
                matches = [i for i in spec['instances'] if i['name'] == block['instance']]
                if len(matches) != 1:
                    row['errors'].append('wrapper instance absent or ambiguous')
                else:
                    inst = matches[0]
                    if inst['module'] != block['module'] or inst['file'] != block['source'] or inst.get('params', {}) != block.get('params', {}):
                        row['errors'].append('wrapper engine source/module/parameters differ from contract')
                    for port, (direction, bits) in ports.items():
                        bind = inst['bind'].get(port)
                        row['ports'].append(dict(port=port, direction=direction, bits=bits, bind=bind))
                        if port in block.get('clock_reset_ports', []):
                            if bind not in ('clk', 'rst_n'):
                                row['errors'].append(f'{port}: clock/reset must use a real wrapper clock/reset')
                            continue
                        choices = bind if isinstance(bind, list) else [bind]
                        if not choices or any(not isinstance(b, str) or not b.startswith('die:') for b in choices):
                            row['errors'].append(f'{port}: functional HGI port is not connected to a die net')
                        else:
                            for b in choices:
                                width = sum(W.parse_rng(x)[2] - W.parse_rng(x)[1] for x in b[4:].split('+'))
                                if width != bits:
                                    row['errors'].append(f'{port}: die mapping {width} bits differs from engine {bits}')
                    try:
                        if row['errors']:
                            raise ValueError('strict regeneration deferred until functional bindings pass')
                        rendered, stats = W.gen(spec, strict=True)
                        path = spec_path.with_name(spec['master'] + '.sv')
                        row['wrapper_sha256'] = digest(path) if path.exists() else None
                        row['ties'] = stats['ties']
                        if not path.exists() or path.read_text() != rendered:
                            row['errors'].append('wrapper differs from strict regeneration')
                    except (Exception, SystemExit) as exc:
                        row['errors'].append(f'strict wrapper generation failed: {exc}')
        errors.extend(f"{row['name']}: {x}" for x in row['errors'])
        rows.append(row)
    if not rows:
        errors.append('empty contract does not establish any generic integration')
    return dict(schema='opentallas.hgi_die_integration_audit.v1',
                scope='strict wrapper bindings only; die_top_lint, remote elaboration, traffic, and physical gates remain mandatory',
                variant=contract['variant'], blocks=rows, errors=errors,
                verdict='FAIL' if errors else 'PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.contract.read_text()))
    result['contract_sha256'] = digest(args.contract)
    result['checker_sha256'] = digest(Path(__file__))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(verdict=result['verdict'], blocks=len(result['blocks']), errors=result['errors']), indent=2))
    return int(result['verdict'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
