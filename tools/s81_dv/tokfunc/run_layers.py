#!/usr/bin/env python3
"""Run existing minimum slice replay vehicles; never qualify a full layer/token.

Usage: run_layers.sh ROOT TREE FIX OUT [L0 L2 L14 L20]
Environment: CUT_ROOT=OUT/prep, KIT_ROOT=CUT_ROOT/cuts,
PROG_ROOT=OUT, PROG_MODE=su, CUTS='cut_0S cut_0N cut_7 cut_3S_ctl',
DIE_V=TREE/results/arch/s81_dv_1016/bind9/die.v.gz, J=4.
Exit 1 means a failed/missing replay; 2 means partial coverage only.
Every invocation requires a fresh OUT/replays directory to preserve failures.
"""
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    root, tree, fix, out = (Path(x).resolve() for x in sys.argv[1:5])
    layers = sys.argv[5:] or ['L0', 'L2', 'L14', 'L20']
    cuts = os.environ.get('CUTS', 'cut_0S cut_0N cut_7 cut_3S_ctl').split()
    cut_root = Path(os.environ.get('CUT_ROOT', str(out / 'prep')))
    kit_root = Path(os.environ.get('KIT_ROOT', str(cut_root / 'cuts')))
    prog_root = Path(os.environ.get('PROG_ROOT', str(out)))
    die = Path(os.environ.get('DIE_V', str(tree / 'results/arch/s81_dv_1016/bind9/die.v.gz')))
    replay_root = out / 'replays'
    replay_root.mkdir(parents=True, exist_ok=False)
    report = dict(schema='opentallas.s81_tokfunc.layers.v1', grade='RTL-functional (source assembly)',
                  root=str(root), tree=str(tree), die_v=str(die), fixtures=str(fix),
                  verdict='RUNNING', full_layer_qualified=False, full_token_qualified=False,
                  coverage='Selected slice cuts only; unrepresented RTL is not qualified.', layers=[])

    def save():
        tmp = out / 'layers_report.json.tmp'
        tmp.write_text(json.dumps(report, indent=2) + '\n')
        tmp.replace(out / 'layers_report.json')

    def run(args, log):
        with log.open('w') as f:
            return subprocess.run([str(a) for a in args], cwd=root, stdout=f,
                                  stderr=subprocess.STDOUT, check=False).returncode

    save()
    for layer in layers:
        prog = prog_root / f'prog_{layer}_{os.environ.get("PROG_MODE", "su")}'
        row = dict(layer=layer, program=str(prog), verdict='RUNNING', cuts=[])
        report['layers'].append(row)
        low = prog / 'lowering.json'
        if not low.exists() or not (fix / layer).is_dir():
            row.update(verdict='FAIL', reason='Missing compiled lowering or layer fixtures')
            save()
            continue
        lowering = json.loads(low.read_text())
        row['lowering_status_counts'] = lowering.get('status_counts', {})
        for cut in cuts:
            dest = replay_root / layer / cut
            dest.mkdir(parents=True)
            item = dict(cut=cut, verdict='RUNNING', replay=str(dest), run=str(dest / 'run'))
            row['cuts'].append(item)
            save()
            cdir, kit = cut_root / 'cuts' / cut, kit_root / ('K_' + cut)
            if not (cdir / 'slice_ports.json').exists() or not (kit / 'kit.json').exists():
                item.update(verdict='FAIL', reason='Missing cut or RTL kit')
                save()
                continue
            rc = run(['python3', root / 'tools/s81_dv/dv_cut_replay.py', 'gen',
                      '--die-v', die, '--prog', prog, '--cut', cdir, '--out', dest], dest / 'gen.log')
            item['gen_rc'] = rc
            if rc:
                item.update(verdict='FAIL', reason='Replay generator refused schedule; see gen.log')
                save()
                continue
            replay = json.loads((dest / 'replay.json').read_text())
            for key in ('partial', 'verdict_kind', 'in_events', 'out_check_lines', 'ncyc', 'unencoded_total'):
                item[key] = replay.get(key)
            # A cut's objects are shared only between layers in this immutable run.
            env = os.environ.copy()
            env['J'] = env.get('J', '4')
            env['OBJ'] = str(out / 'builds' / cut / 'obj')
            with (dest / 'sim.log').open('w') as f:
                rc = subprocess.run(['bash', str(root / 'tools/s81_dv/run_dv_slice.sh'), str(kit),
                    str(dest / 'run'), f'+IN={dest}/in.txt', f'+OUT={dest}/out.txt',
                    f'+TRACE={dest}/run/trace.txt', f'+NCYC={replay["ncyc"]}'],
                    cwd=root, env=env, stdout=f, stderr=subprocess.STDOUT, check=False).returncode
            item['sim_rc'] = rc
            check_rc = run(['python3', root / 'tools/s81_dv/dv_cut_replay.py', 'check',
                           '--replay', dest, '--run', dest / 'run', '--out', dest / 'check.json'],
                           dest / 'check.log')
            item['check_rc'] = check_rc
            item['verdict'] = 'FAIL' if rc or check_rc else (
                'PARTIAL' if replay['partial'] or replay['verdict_kind'] != 'SCHEDULE'
                or replay['in_events'] == 0 or replay['out_check_lines'] == 0 else 'PASS')
            save()
        row['verdict'] = 'FAIL' if any(c['verdict'] == 'FAIL' for c in row['cuts']) else 'PARTIAL'
        save()
    report['verdict'] = 'FAIL' if any(r['verdict'] == 'FAIL' for r in report['layers']) else 'PARTIAL'
    save()
    print(json.dumps(report))
    return 1 if report['verdict'] == 'FAIL' else 2


if __name__ == '__main__':
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    sys.exit(main())
