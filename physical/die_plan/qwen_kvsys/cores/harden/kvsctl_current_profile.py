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


def materialize(core_path, pins, diagnostic, out, repo, parent=None, all_private_out=False, boot_capture=False):
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
                  bw_valid='opt-in bpin receiver factorization; whole-profile proof required',
                  face_proof_environment={'HR_FULL_FLATTEN': '1', 'HR_EXTRA_MACROS': 'eq/t:ctl_sram*',
                                          'HR_PRESERVE_PORT_SHAPE': '1',
                                          'HR_ALL_PRIVATE_OUT': '1' if all_private_out else '0'},
                  still_open='private output copies, current boundary synthesis, physical signoff')
    if boot_capture:
        # DIE-KV-60 ctlin: +1 boot-only capture of every external u_boot input, gold AND gate (declared like the
        # +1 dcfg landings), so the face / profile proofs compare like with like
        sys.path.insert(0, str(here))
        import kvsctl_boot_capture
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
            if boot_capture and name == 'qkd_kvs_ctl_nc32__leaf.sv':
                text, ledger['boot_capture'] = kvsctl_boot_capture.apply(text)
                ledger['boot_cycles_added'] = spec.get('boot_cycles_added', 0) + 1
            if mode == 'gate' and name == 'qkd_kvs_ctl_nc32__leaf.sv':
                old = 'qkd_kv_es_fan_root2_b_nc32 #('
                if text.count(old) != 1:
                    raise ValueError('expected the one current fan-root instance')
                text = text.replace(old, 'qkd_kv_es_fan_root2_b_nc32_bpin #(', 1)
            (dest / name).write_text(text)
            replacements[name] = str((dest / name).resolve())
        mode_files = [replacements.get(Path(f).name, f) for f in narrowed['files']]
        if mode == 'gate':
            bpin = repo / 'rtl/qwen_sys/static_kv_die_20261017/qkd_kv_es_fan_root2_b_nc32_bpin.sv'
            if not bpin.is_file():
                raise ValueError('missing the opt-in current bpin receiver source')
            mode_files.append(str(bpin.resolve()))
        receipt = dict(narrowed, files=mode_files,
                       landing=ledger)
        (dest / 'core.json').write_text(json.dumps(receipt, indent=2))
    (out / 'landing_ledger.json').write_text(json.dumps(ledger, indent=2))
    if parent is not None:
        subprocess.run([sys.executable, str(here / 'kvsctl_rebind.py'), str(parent),
                        str(out / 'wire/dead_drop.json'), str(out / 'wire/qkd_kvs_ctl.sv'),
                        str(out / 'narrowed_parent.sv'), str(out / 'parent_rebind.json')], check=True)
        rebind = json.loads((out / 'parent_rebind.json').read_text())
        if rebind['verdict'] != 'PASS' or rebind['dropped_bits'] != len(dead):
            raise ValueError('current parent dead-piece rebind failed')
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core-json', required=True, type=Path)
    parser.add_argument('--pins', required=True, type=Path)
    parser.add_argument('--diagnostic', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[5])
    parser.add_argument('--parent', type=Path, help='optional current strict-bound hub_C parent to rebind')
    parser.add_argument('--all-private-out', action='store_true', help='larger alternative: clone every registered output')
    parser.add_argument('--boot-capture', action='store_true',
                        help='DIE-KV-60 ctlin: one plain capture flop per external u_boot input bit (boot +1 edge)')
    args = parser.parse_args()
    print(json.dumps(materialize(args.core_json, args.pins, args.diagnostic, args.out, args.repo, args.parent,
                                 args.all_private_out, args.boot_capture)))


if __name__ == '__main__':
    main()
