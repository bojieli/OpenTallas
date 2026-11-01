#!/usr/bin/env python3
"""Materialize the approved ctl boundary repair on current source dependencies.

This creates an opt-in candidate, never edits canonical RTL or enables a recipe.
All declared-dead pins come from the current synthesized boundary diagnostic.
The comparison reference mirrors only the declared +1 static boot visibility;
the gate additionally applies the 166-bit zero-cycle retimes. Datapath reset
policy and the mission schedule remain unchanged. Private output copies follow
after the retime miter, using hr_face_ports.py and its mutant receipt.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def replace_checked(text, pairs):
    for pair in pairs:
        old, new = pair['old'], pair['new']
        if not old or text.count(old) != 1:
            raise ValueError('current ctl source changed; re-derive retime context: ' + old[:100])
        text = text.replace(old, new, 1)
    return text


def materialize(core_path, pins, diagnostic, out, repo):
    here = Path(__file__).resolve().parent
    spec = json.loads((here / 'kvsctl_current_face_changes.json').read_text())
    core = json.loads(core_path.read_text())
    if core['module'] != 'qkd_kvs_ctl':
        raise ValueError('expected current qkd_kvs_ctl')
    files = [Path(f) if Path(f).is_absolute() else repo / f for f in core['files']]
    by_name = {f.name: f for f in files}
    diag = json.loads(diagnostic.read_text())
    dead = [item.split(':', 1)[0] for item in diag['fails']['dropped']]
    if len(dead) != diag['fail_counts']['dropped']:
        raise ValueError('need the complete current dead-pin diagnostic, not a truncated summary')
    if out.exists() and any(out.iterdir()):
        raise ValueError('candidate output already exists; preserve it and use a fresh directory')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'dead_report.json').write_text(json.dumps({'dropped_in': dead}, indent=2))
    absolute_core = dict(core, files=[str(f.resolve()) for f in files])
    (out / 'current_core.json').write_text(json.dumps(absolute_core, indent=2))
    subprocess.run([sys.executable, str(here / 'kvsctl_dead_drop.py'), str(by_name['qkd_kvs_ctl.sv']),
                    str(out / 'dead_report.json'), str(out / 'wire'), '--pins', str(pins),
                    '--core-json', str(out / 'current_core.json')], check=True)
    narrowed = json.loads((out / 'wire/qkd_kvs_ctl_core.json').read_text())
    ledger = {key: value for key, value in spec.items() if key != 'changes'}
    ledger.update(dead_input_bits_removed=len(dead), pins=narrowed['pin_bits'], default_enabled=False,
                  parent_binding='requires the matching dead-piece rebind before adoption',
                  still_open='embgw__bw[0]: sender must preserve the full bus timing')
    for mode in ('gate', 'gold'):
        dest = out / mode
        dest.mkdir()
        replacements = {}
        for name, pairs in spec['changes'].items():
            text = by_name[name].read_text()
            if mode == 'gate' or name == 'qkd_kvs_ctl_nc32__leaf.sv':
                text = replace_checked(text, pairs)
            if mode == 'gold' and name == 'qkd_kvs_ctl_nc32__leaf.sv':
                if text.count(', .IN_LAND(1)') != 8:
                    raise ValueError('expected exactly the eight approved cf2 input retimes')
                text = text.replace(', .IN_LAND(1)', '')
            (dest / name).write_text(text)
            replacements[name] = str((dest / name).resolve())
        receipt = dict(narrowed, files=[replacements.get(Path(f).name, f) for f in narrowed['files']],
                       landing=ledger)
        (dest / 'core.json').write_text(json.dumps(receipt, indent=2))
    (out / 'landing_ledger.json').write_text(json.dumps(ledger, indent=2))
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core-json', required=True, type=Path)
    parser.add_argument('--pins', required=True, type=Path)
    parser.add_argument('--diagnostic', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[5])
    args = parser.parse_args()
    print(json.dumps(materialize(args.core_json, args.pins, args.diagnostic, args.out, args.repo)))


if __name__ == '__main__':
    main()
