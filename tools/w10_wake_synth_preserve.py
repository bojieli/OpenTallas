#!/usr/bin/env python3
"""Fail-closed companion synthesis patch for the modeled eight wake registers.

Generate a private ORFS script; never modify the platform or original runner.
The final mapped guard is still mandatory before physical admission.
"""
import argparse
import hashlib
import json
from pathlib import Path


def retain(stage):
    typ = '{t:$adff}' if stage == 'proc' else '{t:$_DFF_*}'
    return '\n'.join([
        '# W10 modeled wake cells: select drivers from eight named wires, not $procdff names.',
        'select -assert-count 8 {w:g_wake.g_leaf*.wake}',
        f'select -set ot_wake_{stage} {{w:g_wake.g_leaf*.wake}} %ci {typ} %i',
        f'select -assert-count 8 @ot_wake_{stage}',
        f'setattr -set keep 1 @ot_wake_{stage}',
        'select -clear',
    ])


def companion(original):
    first = '  synth -flatten -run :fine {*}$synth_full_args'
    # This pinned flat-flow branch must occur exactly once. Other modes are rejected.
    if original.count(first) != 2:
        raise ValueError('ORFS flat synthesis branch drift: expected checkpoint and normal branches')
    branch = '} elseif { !$::env(SYNTH_HIERARCHICAL) } {\n  # Perform standard coarse-level synthesis script, flatten right away\n' + first
    if original.count(branch) != 1:
        raise ValueError('ORFS normal flat branch drift')
    # Tcl reserves proc for procedure definitions; call the Yosys command explicitly.
    original = original.replace(branch, branch[:-len(first)] + '  yosys proc\n  flatten\n' + retain('proc') + '\n' + first)
    fine = '  synth -top $::env(DESIGN_NAME) -run fine: -noabc {*}$synth_full_args'
    if original.count(fine) != 1:
        raise ValueError('ORFS fine synthesis branch drift')
    replacement = '\n'.join([
        '  # Same no-ABC fine-stage operations, with a narrow retention barrier after techmap.',
        '  if {$synth_full_args ne "-extra-map $::env(FLOW_HOME)/platforms/common/lcu_kogge_stone.v"} {',
        '    error "W10 wake retention requires the pinned default arithmetic mapping arguments"',
        '  }',
        '  opt -fast -full', '  memory_map', '  opt -full',
        '  techmap -map +/techmap.v -map $::env(FLOW_HOME)/platforms/common/lcu_kogge_stone.v',
        retain('techmap'), '  opt -fast', '  hierarchy -check', '  stat', '  check',
    ])
    return '# W10 private companion; original ORFS script hash is recorded by generator.\n' + original.replace(fine, replacement)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--original', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit('refusing to overwrite a synthesis script')
    patched = companion(args.original.read_text())
    args.out.write_text(patched)
    args.out.with_suffix('.provenance.json').write_text(json.dumps(dict(
        original_sha256=hashlib.sha256(args.original.read_bytes()).hexdigest(),
        companion_sha256=hashlib.sha256(patched.encode()).hexdigest(),
        scope='proc and post-techmap driver cells only; final full-map/exact/lease gates remain required',
        adopted=False, physical_admission=False), indent=2)+'\n')
