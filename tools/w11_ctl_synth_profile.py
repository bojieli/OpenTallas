#!/usr/bin/env python3
"""Profile the full W11 controller vehicle before and after generic optimization.

Diagnostic evidence only: this does not map cells or claim timing closure.
"""
import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['rtl/chip/physical/ot_v41_attn_eng_ctl_endpoint_phys.sv', 'rtl/hdc/v41x/ot_hdc_v41x_attn_ctl_phys.sv']
TOP = 'ot_v41_attn_eng_ctl_phys'


def summarize(path):
    design = json.loads(path.read_text())['modules']
    bits = collections.Counter()
    instances = collections.Counter()

    def visit(module, prefix=''):
        for name, cell in design[module]['cells'].items():
            full = prefix + name
            if cell['type'] in design:
                instances[cell['type']] += 1
                visit(cell['type'], full + '.')
            elif 'dff' in cell['type'].lower():
                if 'g_t[' in full:
                    kind = 'tile_sinks'
                elif 'g_tr[' in full:
                    kind = 'transposer_sinks'
                elif 'g_m[' in full:
                    kind = 'merge_sinks'
                elif 'g_ln[' in full:
                    kind = 'lane_trees'
                elif 'u_sbuf' in full or 'u_stage' in full:
                    kind = 'staging'
                else:
                    kind = 'other'
                bits[kind] += len(cell['connections']['Q'])
    visit(TOP)
    return dict(register_bits_total=sum(bits.values()), register_bits_by_region=dict(bits),
                module_instances=dict(instances))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--preserve-endpoints', action='store_true')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    params = dict(BREG=1, D=512, NSTAGE=2, PHYS=1, REPL=2)
    from run_abi3_physical import w11_controller_endpoint_commands
    keep = w11_controller_endpoint_commands(dict(top=TOP, parameters=params,
                                                preserve_w11_controller_endpoints=a.preserve_endpoints))
    commands = [*[f'read_verilog -sv {ROOT / p}' for p in SOURCES],
                f'hierarchy -check -top {TOP}' + ''.join(f' -chparam {k} {v}' for k, v in params.items()),
                'proc', 'opt_clean', f'write_json {a.out.resolve() / "elaborated.json"}',
                *keep, 'flatten', 'opt -full', 'memory_map', 'opt -full',
                f'write_json {a.out.resolve() / "optimized.json"}',
                'techmap', 'opt -fast',
                f'write_json {a.out.resolve() / "bit_optimized.json"}']
    script = a.out / 'profile.ys'
    script.write_text('\n'.join(commands) + '\n')
    yosys = Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'
    with (a.out / 'yosys.log').open('w') as log:
        run = subprocess.run([str(yosys), '-T', '-s', str(script)], stdout=log, stderr=subprocess.STDOUT)
    assert run.returncode == 0, a.out / 'yosys.log'
    rec = dict(schema='opentallas.w11-controller-synthesis-profile.v1',
               source_commit=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
               parameters=params, preserve_endpoints=a.preserve_endpoints,
               model=dict(H=16, D=512, TD=32, NL=4, tiles=64, products_per_cycle=32768,
                                             kv_in_bits=4*16*265, q_bits=512*16, p_in_bits=2*32*16,
                                             pv_out_bits=64*16*32),
               claim='Elaboration and generic optimization only. No mapped sequential or SS/FF timing claim.',
               source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
               stages={n: summarize(a.out / (n + '.json')) for n in ['elaborated', 'optimized', 'bit_optimized']})
    (a.out / 'profile.json').write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps(rec['stages'], indent=2))


if __name__ == '__main__':
    main()
