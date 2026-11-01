#!/usr/bin/env python3
"""Prepare the KV profile ROM from the SAME calendar image used by a QC+KV pair.

The original runtime is immutable. The compiled ROM model keeps its relative
VIAMAP path; a new runtime directory supplies actual newly compiled profile
bytes there. No RTL, macro shape, boot pipeline or timing contract changes.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/mem_compiler'))
import kv_dcal_profile as P


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(path):
    rows = [int(line, 16) for line in path.read_text().splitlines()]
    if len(rows) != 32:
        raise ValueError('expected32 physical rows in the actual64x32m2 profile')
    return [sum(((rows[a//2] >> (2*b+a%2)) & 1) << b for b in range(32)) for a in range(64)]


def prepare(original, image, output):
    old = json.loads((original / 'runtime_rom.json').read_text())
    old_path = (original / old['runtime_path']).resolve(strict=True)
    if sha(old_path) != old['sha256']:
        raise ValueError('original KV profile no longer matches its receipt')
    output.mkdir(parents=True, exist_ok=False)
    profile = P.extract_sv(image.read_text())
    emitted = P.personalise(profile, output / 'compiled_profile', instance='kv_dcal')
    source = output / 'compiled_profile' / emitted['viamap']
    words = P.pack_profile(profile)
    if decode(source) != words:
        raise ValueError('compiled native profile bits disagree with selected pair calendar')
    old_words = decode(old_path)
    delta = [dict(address=i, old=old_words[i], selected=words[i]) for i in range(64) if old_words[i] != words[i]]
    target = output / old['runtime_path']
    target.parent.mkdir(parents=True, exist_ok=True)
    os.link(source, target)
    runtime = dict(old, viamap=str(source.resolve()), sha256=sha(source),
                   source_pair_image=str(image.resolve()), source_pair_image_sha256=sha(image),
                   original_runtime=str(original.resolve()), original_sha256=old['sha256'],
                   logical_word_changes=delta, selected_profile=profile,
                   hardware_cycle_delta=0,
                   scope='Selected pair calendar data only; original runtime unchanged; no token qualification.')
    (output / 'runtime_rom.json').write_text(json.dumps(runtime, indent=2) + '\n')
    return runtime


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-kv-run', type=Path, required=True)
    parser.add_argument('--pair-image', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.original_kv_run, args.pair_image, args.out)
    print(json.dumps(dict(sha256=result['sha256'], changes=result['logical_word_changes'],
                         selected_first=result['selected_profile']['FIRST_OFS'],
                         selected_admission=result['selected_profile']['ADM_LEN']), sort_keys=True))
