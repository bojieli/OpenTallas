#!/usr/bin/env python3
"""Extract the first norm's entry/CTL/NX phase as a small arithmetic vehicle.

This ends before the spontaneous quant trains and makes no full-layer claim.
The original programme and every failure remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def extract(source, destination, nx_delta=0):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise ValueError('fresh output directory required: ' + str(destination))
    schedule = json.loads((source / 'schedule.json').read_text())
    events = []
    for e in schedule['events']:
        tag = e.get('tag', '')
        if (tag.startswith('entry.') or tag in ('attn.HLOAD', 'attn.GAIN', 'attn.XFIN_GO')
                or tag.startswith('attn.NORMR.k') or e.get('kind') in ('NX', 'LKFRAME')):
            if e.get('kind') == 'NX' and nx_delta:
                e = dict(e, cycle=e['cycle'] + nx_delta,
                         words=[[edge + nx_delta, value, mask] for edge, value, mask in e['words']])
            events.append(e)
    if not any(e.get('kind') == 'NX' and e.get('words') for e in events):
        raise ValueError('source contains no encoded NX arithmetic checks')
    shutil.copytree(source, destination)
    phase = dict(name='attn.entry_norm_nx', full_layer=False,
                 source_schedule_sha256=hashlib.sha256((source / 'schedule.json').read_bytes()).hexdigest(),
                 included_events=len(events), excluded_events=len(schedule['events']) - len(events),
                 nx_timing_delta=nx_delta,
                 scope='hc_pre plus per-leaf square and chunk8 sums; no rstd/quant or later layer ops')
    schedule.update(events=events, phase=phase)
    payload = json.dumps(schedule, indent=1) + '\n'
    (destination / 'schedule.json').write_text(payload)
    manifest = json.loads((destination / 'manifest.json').read_text())
    manifest['phase'] = phase
    if isinstance(manifest.get('files'), dict) and 'schedule.json' in manifest['files']:
        manifest['files']['schedule.json'] = hashlib.sha256(payload.encode()).hexdigest()
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    return phase


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination')
    parser.add_argument('--nx-delta', type=int, default=0,
                        help='explicit output/peer-NX timing correction for an older compiled model')
    args = parser.parse_args()
    print(json.dumps(extract(args.source, args.destination, args.nx_delta)))
