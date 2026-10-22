#!/usr/bin/env python3
"""Prepare a NEW captured successor after publication; never edits input runs.

Usage: stage_saved_successor.py --original F --health REPAIRED_HEALTH_RUN
    --source FRESH_PUBLISHED_SOURCE --out NEW_SUCCESSOR
This performs file staging only. No GEN, bind, gate, or chain is launched.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'health', 'source', 'out'):
        p.add_argument('--' + name, required=True, type=Path)
    a = p.parse_args()
    original, health, source, out = [getattr(a, n).resolve() for n in ('original', 'health', 'source', 'out')]
    if out.exists():
        raise SystemExit('refuse existing successor: ' + str(out))
    if out == original or out == health or original in out.parents or health in out.parents:
        raise SystemExit('successor must be separate from immutable input runs')
    current = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--', 'tools', 'rtl', 'physical'], text=True).strip():
        raise SystemExit('published source tree is dirty')
    hp = json.loads((health / 'health_plane.json').read_text())
    audit = hp['audit']
    if (audit['far_inputs'] or audit['source_coverage']['missing'] or not audit['sink_is_sticky']
            or hp['blockers'] or hp['unadmitted'] or not hp['status']['fits_reserved']):
        raise SystemExit('repaired health stage is not a strict PASS')
    if hp['sources'] != 298 or hp['transports'] != 85:
        raise SystemExit('unexpected saved health inventory; do not alias a different case')
    needed_case = ['die.v', 'place.tcl', 'elements.lef', 'die.v.pads.json', 'die.v.params.json']
    for n in needed_case:
        if not (health / 'case_kv' / n).is_file():
            raise SystemExit('missing repaired health object: ' + n)
    # Original F prehealth inputs must be the exact ones the replay consumed.
    for relative, digest in hp['inputs'].items():
        base = original / relative
        prehealth = base.with_name(base.name + '.prehealth')
        actual = prehealth if prehealth.exists() else base
        if sha(actual) != digest:
            raise SystemExit('captured input drift: ' + relative)
    out.mkdir()
    archived = out / 'captured_original'; archived.mkdir()
    for name in ('case_kv', 'libs', 'lint'):
        if (original / name).exists():
            shutil.copytree(original / name, out / name)
    # Archive every original report; carry only unchanged runtime/source inputs.
    # In particular old port_bind.json and partial lane reports cannot be a new PASS.
    top_archive = archived / 'top_level'; top_archive.mkdir()
    unchanged = {'d2ds_view.json', 'fwd_lanes.json', 'kv_flags.env',
                 'lane_stations.json', 'lane_views.tsv', 'relays.json',
                 'rly_std.json', 'rst_hold_view_audit.json',
                 'rst_pin_view_audit.json', 'rst_regional.json', 'tile_views.json'}
    for src in original.iterdir():
        if src.is_file() and src.suffix in ('.json', '.env', '.tsv', '.csv'):
            shutil.copy2(src, top_archive / src.name)
            if src.name in unchanged:
                shutil.copy2(src, out / src.name)
    for src in original.iterdir():
        if src.is_file() and ('DIAGNOSTIC' in src.name or src.name in ('NOT_A_DIE_RESULT', 'READY_FOR_CHAIN')):
            shutil.copy2(src, archived / src.name)
            if src.name not in ('HEALTH_DIAGNOSTIC', 'READY_FOR_CHAIN'):
                shutil.copy2(src, out / src.name)
    for n in needed_case:
        shutil.copy2(health / 'case_kv' / n, out / 'case_kv' / n)
    for n in ('expand.json', 'health_plane.json', 'health_successor.json'):
        shutil.copy2(health / n, out / n)
    for src in (health / 'libs').iterdir():
        if src.is_file():
            shutil.copy2(src, out / 'libs' / src.name)
    if (original / 'health_plane.json').exists():
        shutil.copy2(original / 'health_plane.json', archived / 'health_plane.json')
    provenance = dict(schema='opentallas.kv_captured_successor_staging.v1',
                      original=str(original), original_gen_source='c6520b2ee',
                      published_source_tree=str(source), published_source_commit=current,
                      original_source_commit=(original / 'case_kv/SOURCE_COMMIT').read_text().strip(),
                      repaired_health_stage=str(health), repaired_health_sha256=sha(health / 'health_plane.json'),
                      captured_input_sha256=hp['inputs'],
                      staged_case_sha256={n: sha(out / 'case_kv' / n) for n in needed_case},
                      whole_die_bind='NOT RUN', ready_for_chain=False,
                      next='import two actual S6C views into copied catalog, then normal post-health PREP gates; no GEN')
    (out / 'captured_stage_provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
