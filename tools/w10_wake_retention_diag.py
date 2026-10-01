#!/usr/bin/env python3
"""Lean eight-register preservation proof; not a full-column or physical gate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from w10_wake_synth_preserve import retain

ROOT = Path(__file__).resolve().parents[1]


def run(output, liberty, yosys='yosys'):
    output.mkdir(parents=True, exist_ok=False)
    original = ROOT/'rtl/v41rom/ot_v41_rom_elem_wake_w10.sv'
    source = original.read_text()
    start = source.index('        for (genvar wg = 0; wg < 8;')
    end = source.index('        assign gclk', start)
    body = source[start:end].replace('for (genvar wg =', 'for (wg =')
    body = body.replace('            ot_hdc_cg u_cg (.clk(clk), .en(wake), .gclk(leaf_clk[wg]));',
                        '            assign leaf_clk[wg] = wake;')
    harness = ('module wake_diag(input clk,rst_n,go,go_e,walk_busy, input [7:0] drain, output [7:0] leaf_clk);\n'
               'genvar wg; generate begin : g_wake\n'+body+'end endgenerate\nendmodule\n')
    src = output/'wake.sv'; src.write_text(harness)
    results = {}
    for mode in ('collapsed', 'first_only', 'second_only', 'both'):
        # retain() emits Tcl-quoted selections; .ys parses selections directly.
        first = retain('proc').replace('{','').replace('}','') if mode in ('first_only', 'both') else ''
        second = retain('techmap').replace('{','').replace('}','') if mode in ('second_only', 'both') else ''
        # Negative second-only must record its failed expected-eight assertion.
        stages = '\n'.join([
            f'read_verilog -sv {src}', 'hierarchy -top wake_diag', 'proc',
            f'write_json {output}/{mode}_proc.json', first,
            'synth -top wake_diag -run coarse:coarse',
            f'write_json {output}/{mode}_coarse.json',
            'opt -fast -full', 'memory_map', 'opt -full', 'techmap',
            f'write_json {output}/{mode}_techmap.json', second,
            'opt -fast', f'dfflibmap -liberty {liberty}', 'opt -fast',
            'abc', 'opt -fast', f'write_json {output}/{mode}_mapped.json',
        ])+'\n'
        script = output/(mode+'.ys'); script.write_text(stages)
        with (output/(mode+'.log')).open('w') as log:
            p = subprocess.run([yosys, '-Q', str(script)], stdout=log, stderr=subprocess.STDOUT)
        observations = {}
        for stage in ('proc', 'coarse', 'techmap', 'mapped'):
            path = output/f'{mode}_{stage}.json'
            if not path.exists(): continue
            module = json.loads(path.read_text())['modules']['wake_diag']
            cells = {n:c for n,c in module['cells'].items() if 'dff' in c['type'].lower()}
            observations[stage] = dict(count=len(cells), cells={n:dict(type=c['type'], attributes=c['attributes']) for n,c in cells.items()},
                                       wake_wire_attributes={n:w['attributes'] for n,w in module['netnames'].items()
                                                             if n.startswith('g_wake.g_leaf') and n.endswith('.wake')})
        results[mode] = dict(returncode=p.returncode, stages=observations)
    valid = (results['both']['returncode']==0 and results['both']['stages']['mapped']['count']==8
             and results['collapsed']['stages']['mapped']['count']==1
             and results['first_only']['stages']['coarse']['count']==8
             and results['second_only']['returncode']!=0
             and results['second_only']['stages']['coarse']['count']==1)
    record = dict(verdict='PASS_LEAN_RETENTION_ONLY' if valid else 'FAIL_LEAN_RETENTION', adopted=False,
                  full_column_qualified=False, physical_admission=False,
                  source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                  liberty_sha256=hashlib.sha256(liberty.read_bytes()).hexdigest(),
                  results=results,
                  first_only_scope='Control observation, not forced FAIL: techmap attribute propagation differs by Yosys version',
                  evidence={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()},
                  pending=['actual full-column mapping: four ROM, eight distinct registered ENAs and full arithmetic flops',
                           'exact clock/reset/transitions', 'all-pin escape/phase/site legality and reserved capacity',
                           'fresh measured fleet lease before any qualified physical context'])
    (output/'receipt.json').write_text(json.dumps(record, indent=2)+'\n')
    return valid


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--liberty',type=Path,required=True)
    ap.add_argument('--yosys',default='yosys')
    args=ap.parse_args()
    raise SystemExit(not run(args.out.resolve(),args.liberty.resolve(),args.yosys))
