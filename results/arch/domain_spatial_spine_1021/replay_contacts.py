#!/usr/bin/env python3
"""Replay sealed source-pinned physical/Liberty contacts through pure admission.

This exercises admission, not OpenROAD collection or spine physical execution.
The latter is owed by integration's actual paired qualification before adoption.
"""
import gzip
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def word(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('[', '\\[').replace(']', '\\]') + '"'


def contacts(rows):
    return '[list ' + ' '.join('[list ' + word(r['terminal']) + ' ' + word(r['root']) + ']' for r in rows) + ']'


def main():
    with gzip.open(HERE/'actual_clock_contacts.json.gz', 'rt') as f:
        fixtures = json.load(f)
    for name, fixture in fixtures.items():
        roots = list(fixture['counts'])
        rootlist = '[list ' + ' '.join(map(word, roots)) + ']'
        rootnets = '[dict create ' + ' '.join(word(r)+' '+word(r) for r in roots) + ']'
        script = 'source ' + word(ROOT/'physical/common_flow/domain_spatial_spine.tcl') + '\n'
        script += 'if {[catch {\nset roots '+rootlist+'\nset nets '+rootnets+'\nset contacts '+contacts(fixture['contacts'])+'\n'
        script += 'set counts [ot_dsp::validate $roots $nets $contacts {}]\n'
        for root, count in fixture['counts'].items():
            script += 'if {[dict get $counts '+word(root)+'] != '+str(count)+'} {error "count mismatch"}\n'
        script += 'if {![catch {ot_dsp::validate $roots $nets [concat $contacts [list [lindex $contacts 0]]] {}}]} {error "duplicate mutant escaped"}\n'
        script += 'if {![catch {ot_dsp::validate $roots $nets [concat $contacts {{unowned/CLK foreign_net}}] {}}]} {error "unowned mutant escaped"}\n'
        script += '} message]} {puts stderr $message; exit 1}\nputs "CONTACT_REPLAY PASS duplicate/unowned mutants caught"\n'
        result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
        if result.returncode or result.stderr:
            raise RuntimeError(f'{name}: {result.returncode}: {result.stderr}')
        print(f'{name} packet={fixture["source_packet"]} mapped={fixture["mapped_sha256"]}')
        print(result.stdout, end='')


if __name__ == '__main__':
    main()
