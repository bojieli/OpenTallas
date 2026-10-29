#!/usr/bin/env python3
"""Join emitted physical START providers to a bound die without adding logic or cycles.

The resulting public top replaces external pst_* inputs with the actual
registered provider instance. Its stage clocks remain explicit clock inputs,
driven by start_stage_emit's patched ctree outputs in physical integration.
"""
import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as D


class ProviderError(ValueError):
    pass


def _module(text, name):
    matches = [m for m in D.parse_modules(text, '<provider-bind>') if m.name == name]
    if len(matches) != 1:
        raise ProviderError(f'expected one definition of {name}, found {len(matches)}')
    return matches[0]


def integrate(top_text, top, provider_text, stages, reset_port):
    """Return successor top text and wiring receipt; original inputs are never mutated."""
    if stages.get('schema') != 'ot_start_stages/1':
        raise ProviderError('unknown START-stage manifest schema')
    original = _module(top_text, top)
    provider = _module(provider_text, 'ot_die_start_stages')
    if original.params:
        raise ProviderError('bound die top must have resolved parameters')
    clock_ports = [s['clock_port'] for s in stages['stages']]
    if len(set(clock_ports)) != len(clock_ports):
        raise ProviderError('duplicate physical stage clock ports')
    ins = sorted({e['net'] for e in stages['die_inputs']})
    outs = sorted({e['net'] for e in stages['die_outputs']})
    reset_inputs=[e['net'] for e in stages.get('reset_inputs',[])]
    virtual_root=any(s.get('root') for s in stages['stages'])
    global_reset=not stages.get('reset_wave') or virtual_root
    expected = {**({'rst_raw_n':'input'} if global_reset else {}), **dict.fromkeys(clock_ports+ins+reset_inputs,'input'), **dict.fromkeys(outs,'output')}
    if set(provider.ports) != set(expected):
        raise ProviderError('provider source header differs from physical stage manifest')
    for name, direction in expected.items():
        dr, ranges = provider.ports[name]
        if dr != direction or ranges not in ([], [('0', '0')]):
            raise ProviderError(f'provider port direction/width mismatch: {name}')
    if reset_port not in original.ports or original.ports[reset_port] != ('input', []):
        raise ProviderError(f'raw reset must be an existing scalar input: {reset_port}')
    actual_pst = {n for n in original.ports if n.startswith('pst_')}
    if actual_pst != set(outs):
        raise ProviderError(f'provider outputs do not cover bound START inputs: missing {sorted(actual_pst-set(outs))[:5]}, '
                            f'extra {sorted(set(outs)-actual_pst)[:5]}')
    for name in outs:
        if original.ports[name] != ('input', []):
            raise ProviderError(f'provider target is not a scalar bound input: {name}')
    for name in ins+reset_inputs:
        if original.ports.get(name) != ('output', []):
            raise ProviderError(f'provider parent START source is not a bound output: {name}')
    if set(clock_ports) & set(original.ports):
        raise ProviderError('stage clock port already exists in the bound top')
    private = top + '__without_start_provider'
    if re.search(r'\bmodule\s+' + re.escape(private) + r'\b', top_text):
        raise ProviderError('private top name already exists')
    renamed, n = re.subn(r'(\bmodule\s+)' + re.escape(top) + r'\b', lambda m: m[1] + private, top_text)
    if n != 1:
        raise ProviderError('bound top definition is not unique')
    renamed = re.sub(r'(\bendmodule\s*:\s*)' + re.escape(top) + r'\b', lambda m: m[1]+private, renamed)
    public = [n for n in original.order if n not in outs] + clock_ports
    lines = [f'// GENERATED physical START-provider join: no added logic/cycles; clocks supplied by patched ctree.',
             f'module {top} (\n    ' + ',\n    '.join(public) + '\n);']
    for name in public:
        dr, ranges = original.ports[name] if name in original.ports else ('input', [])
        width = ''.join(f'[{a}:{b}]' for a, b in ranges)
        lines.append(f'    {dr} wire {width} {name};')
    lines += [f'    wire {name};' for name in outs]
    lines.append(f'    {private} u_bound (' + ', '.join(f'.{n}({n})' for n in original.order) + ');')
    binds = {**({'rst_raw_n':reset_port} if global_reset else {}), **{n:n for n in clock_ports+ins+outs+reset_inputs}}
    lines.append('    ot_die_start_stages u_start_provider (' + ', '.join(f'.{n}({binds[n]})' for n in provider.order) + ');')
    lines.append('endmodule')
    receipt = dict(form='physical_start_provider_join', top=top, private_top=private,
                   provider='ot_die_start_stages', stage_clock_inputs=clock_ports, driven_start_inputs=outs,
                   parent_start_outputs=ins, reset_port=reset_port, logical_cycles_added=0,
                   physical_stage_count=len(stages['stages']), physical_flops=stages['counts']['flops'],
                   physical_timing='NOT RUN: clock/load/phase gates must run on the integrated physical source')
    return renamed + '\n' + '\n'.join(lines) + '\n', receipt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('top_source'); ap.add_argument('--top', required=True)
    ap.add_argument('--provider', required=True); ap.add_argument('--stages', required=True)
    ap.add_argument('--reset-port', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    text, receipt = integrate(Path(a.top_source).read_text(), a.top, Path(a.provider).read_text(),
                              json.loads(Path(a.stages).read_text()), a.reset_port)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(text)
    out.with_suffix('.json').write_text(json.dumps(receipt, indent=1))
    print(json.dumps({k:v for k,v in receipt.items() if not isinstance(v,list)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
