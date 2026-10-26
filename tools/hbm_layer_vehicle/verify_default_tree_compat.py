#!/usr/bin/env python3
"""Pure compiler comparison: post-prestate-fix default commands before/after tree48 ABI."""
import argparse
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixtures', type=Path, required=True)
    ap.add_argument('--qop', type=Path, required=True)
    ap.add_argument('--boundary', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--baseline', default='8e14d6cd67890acb23770ee495f87b8b426f04c4')
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    old = a.out / 'baseline_source'
    old.mkdir(parents=True, exist_ok=True)
    archive = subprocess.check_output(['git', 'archive', a.baseline, 'tools'], cwd=root)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
        tf.extractall(old, filter='data')
    # Both compilers consume identical frozen programme/schedule inputs.
    # Only the Python compiler revision differs; no input fixture is modified.
    for directory in ('results', 'rtl', 'physical'):
        if not (old/directory).exists():
            (old/directory).symlink_to(root/directory, target_is_directory=True)
    records = []
    for label, src in [('baseline', old), ('candidate', root)]:
        out = a.out / label
        for lay in (0, 2, 14):
            fixture = a.fixtures / f'L{lay:02}'
            cmd = ['python3', str(src/'tools/hbm_layer_vehicle/layer_images.py'), '--design', 'ds', '--layer', str(lay), '--programme', str(fixture/f'images/ds_v41_1M_L{lay:02}_per_die.json'), '--fixtures', str(fixture), '--boundary', str(a.boundary), '--native-read-return', '18', '--native-write-return', '15', '--out', str(out/f'ds_l{lay}')]
            subprocess.run(cmd, cwd=src, check=True, stdout=subprocess.DEVNULL)
        for stage in ('L0', 'chain'):
            subprocess.run(['python3', str(src/'tools/hbm_layer_vehicle/qwen_layer_images.py'), 'emit', '--stage', stage, '--ranks', '0,5', '--boundary', str(a.boundary), '--operands', str(a.qop/f'operands_{stage}.npz'), '--native-read-return', '18', '--native-write-return', '15', '--out', str(out/'qw')], cwd=src, check=True, stdout=subprocess.DEVNULL)
    rels = [Path(f'ds_l{x}') for x in (0,2,14)] + [Path(f'qw/{s}/r{r}') for s in ('L0','chain') for r in (0,5)]
    for rel in rels:
        dirs = [a.out/x/rel for x in ('baseline','candidate')]
        reps = [json.loads((d/'replay.json').read_text()) for d in dirs]
        # Compare numerical values, widths may add only leading zeroes.
        def normal(events):
            return [dict(e, **{k:int(e[k],16) for k in ('val','mask') if k in e}) for e in events]
        assert normal(reps[0]['events']) == normal(reps[1]['events']), f'commands/preloads/checks/cycles changed: {rel}'
        nwords = 0
        for q in dirs[0].glob('images/su_prog*/quarter.mem'):
            new = dirs[1]/q.relative_to(dirs[0])
            before = [int(x,16) for x in q.read_text().split()]
            after = [int(x,16) for x in new.read_text().split()]
            assert before == after, f'numerical quarter words changed: {rel}/{q.name}'
            assert all(x >> 2422 == 0 for x in after), 'default tree command not zero'
            nwords += len(after)
        records.append(dict(case=str(rel),events=len(reps[0]['events']),quarter_words=nwords,commands_preloads_checks_and_cycles_identical=True,default_tree_bits_zero=True))
    receipt = dict(status='PASS_PURE_DEFAULT_COMPATIBILITY',baseline_revision=a.baseline,candidate_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),connected_lowering=False,hardware_executed=False,baseline_command_bits=2422,candidate_command_bits=2470,baseline_boundary_sha256=hashlib.sha256(a.boundary.read_bytes()).hexdigest(),cases=records)
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
