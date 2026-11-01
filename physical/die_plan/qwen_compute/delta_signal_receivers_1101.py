#!/usr/bin/env python3
"""Use a dedicated driven receiver only for the two declared QC glue control pads; preserve package-ID models."""
import json
import sys
from pathlib import Path
plan, manifest = map(Path, sys.argv[1:3])
p = json.loads(plan.read_text())
found = []
for e in p['partition_types']['glue']['contents']:
    if e['inst'] in ('u_bump_fwd_epoch', 'u_bump_fwd_lrst'):
        e['module'] = 'qfd_sigbump_input'
        for b in e['bump_ports']:
            b.pop('model_default', None)
        found.append(e['inst'])
assert len(found) == 2, found
plan.write_text(json.dumps(p) + '\n')
a = json.loads(manifest.read_text())
rule = dict(inst='bump_fwd_(?:epoch|lrst)', module='qfd_sigbump_input',
    reason='Declared package epoch/reset control line side; exact source output preserved, pad_i exported by bump_ports')
a['substitute_inst'] = [r for r in a.get('substitute_inst', []) if r.get('inst') != rule['inst']] + [rule]
manifest.write_text(json.dumps(a, indent=1) + '\n')
