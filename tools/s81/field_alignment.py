"""Check transaction age of actual generated q-element input paths.

This is a structural gate, not arithmetic or physical signoff. Both input
halves originate at the same column FIFO transaction. Unrecognised glue or
multiple drivers are failures rather than assumed zero-latency edges.

ds-1010 lat-audit (2026-10-10): the element's go is checked against its x0 as
well.  go leaves the column FIFO in the cc lane (the same transaction as x0),
climbs the slot stations, enters the pair sequencer (ot_s81_cfg7_seq lc;
go_e = go && act is combinational) and reaches the element through the go
relays and its boundary bank.  The element captures an x beat only while its
walker runs (ot_v41_rom_elem_pq_w10 hit_q = n_run && xs_v && tag match), and
the spine streams an op's beats right after its go, so a go older than x0 at
the element loses the first beats; a go younger than x0 eats the spine's GAP
window.  --mutant-go-relay N adds N cycles to every go path (negative control:
the gate must FAIL).
"""
import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path


def analyze(model, go_extra=0):
    instances = {it.name: it for it in model['insts']}
    drivers = {}
    for name, cls, width, endpoints in model['buses']:
        if len(endpoints) < 2:
            continue
        for endpoint in endpoints[1:]:
            drivers.setdefault(tuple(endpoint), []).append(tuple(endpoints[0]))

    @lru_cache(None)
    def input_age(name, port):
        choices = drivers.get((name, port), [])
        if len(choices) != 1:
            raise ValueError(f'{name}.{port}: expected one driver, got {choices}')
        return output_age(*choices[0])

    @lru_cache(None)
    def output_age(name, port):
        it = instances[name]
        if it.kind == 'cfifo' and port in ('xa', 'xb', 'cc'):
            return name, 0
        if it.kind == 'seq' and port == 'go_e':           # go_e = go && act: combinational from lc
            source, age = input_age(name, 'lc')
            return source, age + go_extra
        if it.kind == 'rly' and port == 'o':
            source, age = input_age(name, 'i')
            return source, age + 1
        if it.kind == 'qbank' and port.startswith('o_'):
            source, age = input_age(name, 'i_' + port[2:])
            return source, age + 1
        if it.kind == 'sstn' and port == 'cc':
            source, age = input_age(name, 'cci')
            return source, age + 1
        if it.kind == 'sstn' and port in ('xa', 'xb', 'qt'):
            source, age = input_age(name, 'xai' if port == 'xa' else 'xbi')
            return source, age + (0 if port == 'qt' else 1)
        raise ValueError(f'{name}.{port}: unpriced stream glue {it.kind}/{it.master}')

    rows, errors = [], []
    for it in model['insts']:
        if it.kind not in ('q', 'bf', 'bf_nv'):
            continue
        try:
            a, b, g = input_age(it.name, 'x0'), input_age(it.name, 'x1'), input_age(it.name, 'go')
            rows.append(dict(element=it.name, frame=it.region,
                             x0=dict(origin=a[0], cycles=a[1]),
                             x1=dict(origin=b[0], cycles=b[1]),
                             go=dict(origin=g[0], cycles=g[1]),
                             go_minus_x0=g[1] - a[1],
                             equal=a == b and g == a))
        except (ValueError, RecursionError) as exc:
            errors.append(dict(element=it.name, error=str(exc)))
    mismatches = [r for r in rows if not r['equal']]
    return dict(gate='generated-field-input-transaction-age',
                scope='full generated q-element input graph; no arithmetic/STA claim',
                q_elements=len(rows) + len(errors), mismatches=mismatches,
                x0_x1_mismatches=sum(r['x0'] != r['x1'] for r in rows),
                go_x0_skew_hist={str(k): sum(r['go_minus_x0'] == k for r in rows)
                                 for k in sorted({r['go_minus_x0'] for r in rows})},
                errors=errors, rows=rows,
                verdict='PASS' if rows and not errors and not mismatches else 'FAIL')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    if not (root / 'dsrom_s81_fulldie.py').is_file():
        root = Path.cwd() / 'tools'
    sys.path.insert(0, str(root))
    import dsrom_s81_fulldie as F
    parser = argparse.ArgumentParser()
    parser.add_argument('options', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mutant-go-relay', type=int, default=0,
                        help='negative control: N extra cycles on every go path (must FAIL)')
    own = parser.parse_args()
    args = F.die_options(argparse.ArgumentParser()).parse_args(own.options.read_text().split())
    F.apply_options(args)
    model = F.build()
    F.finalize_r8(model)
    result = analyze(model, own.mutant_go_relay)
    result['options'] = own.options.read_text()
    own.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'mismatches')}, indent=2))
    for r in result['mismatches'][:8]:
        print('MISMATCH', r['element'], r['frame'], 'x0', r['x0']['cycles'], 'x1', r['x1']['cycles'], 'go', r['go']['cycles'])
    print('mismatched elements', len(result['mismatches']))
    sys.exit(result['verdict'] != 'PASS')
