#!/usr/bin/env python3
"""Prepare one DISABLED BF descriptor overlay; never enable a native cohort.

Accepts actual field/image inputs and an already source-qualified retained
phase. This is a narrow image transformation, not a fresh functional replay.
"""
import argparse
import importlib.util
import json
from pathlib import Path


def decode(physical):
    return [sum(((physical[a // 8] >> (8 * b + a % 8)) & 1) << b
                for b in range(72)) for a in range(4096)]


def encode(words):
    physical = [0] * 512
    for a, word in enumerate(words):
        for b in range(72):
            physical[a // 8] |= ((word >> b) & 1) << (8 * b + a % 8)
    return physical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('current', 'retained', 'profile', 'field', 'compiler', 'out'):
        parser.add_argument('--' + key, required=True, type=Path)
    a = parser.parse_args()
    current = json.loads(a.current.read_text())
    retained = json.loads(a.retained.read_text())
    p, old = current['phase'], retained['phase']
    assert current['frame'] == retained['frame']
    assert current['master'] == retained['master']
    for key in ('phase', 'op', 'fmt', 'rows', 'row_index', 'seg', 'nseg', 'sbase',
                'nbeat', 'bf_pairs', 'assign', 'sel', 'kseg', 'xbase', 'shape'):
        assert p[key] == old[key], key
    assert p['plan']['rows_vals'] == old['plan']['rows_vals']
    assert p['desc'] == {} and p['calendar'] == 'calendar_unmeasured'
    assert old['calendar'] == 'measured_bf_active_idle_q'
    assert old['faults'] == 0 and old['ret_words'] == p['rows']
    profile = json.loads(a.profile.read_text())[p['shape']]
    assert profile['asbuilt_source_qualification']['status'] == 'PASS_STATIC_REPLAY'
    spec = importlib.util.spec_from_file_location('bc', a.compiler)
    bc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bc)
    a.out.mkdir(parents=True, exist_ok=False)
    changes, programmes = [], {}
    for pair in p['bf_pairs']:
        d = old['desc'][str(pair)]
        assert d == dict(profile['fits'][str(pair)]['descriptor'],
                         base=current['actual_ROM_base'][str(pair)])
        packed = bc.pack(d)
        programmes[str(pair)] = dict(descriptor=d, packed_82=packed,
                                    issues=[bc.word(d, i) for i in range(d['n'])])
        for bank in range(4):
            name = f"{current['frame']}_c{pair}_{bank}.viamap.hex"
            raw = [int(v, 16) for v in (a.field / 'images' / name).read_text().split()]
            assert len(raw) == 512
            words = decode(raw)
            address = 4 * p['phase']
            assert words[address] >> 48 == 0, 'preserve existing descriptors'
            spare = (packed >> (24 * bank)) & 0xffffff
            words[address] |= spare << 48
            transformed = encode(words)
            assert all(((x ^ y) & ((1 << 384) - 1)) == 0
                       for x, y in zip(raw, transformed))
            assert [i for i, (x, y) in enumerate(zip(decode(raw), words)) if x != y] in ([], [address])
            if raw != transformed:
                (a.out / name).write_text(''.join(f'{v:0144x}\n' for v in transformed))
                changes.append(dict(image=name, bank=bank, logical_row=address,
                                    physical_row=address // 8, upper24=spare))
    report = dict(status='DISABLED_ONE_PHASE_IMAGE_OVERLAY', production_enabled=False,
                  frame=current['frame'], phase=p['phase'], op=p['op'], rows=p['rows'],
                  descriptors=len(programmes), changed_images=len(changes), changes=changes,
                  programmes=programmes, retained_returns=old['ret'],
                  original_lower48_preserved=True, other_logical_rows_preserved=True,
                  weight_stream_phase_images_untouched=True, added_RTL_cycles=0,
                  source_profile_checks=current['profile_source_checks'],
                  qualification='Retained BF-active/Q-idle source only; current production NOT qualified',
                  holds=['coherent selected source/manifest/schedule qualification',
                         'native reset/family/profile correspondence',
                         'actual activation residency/source epochs', 'BF row tags',
                         'Q/BF overlap and mission calendar'])
    (a.out / 'overlay.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'descriptors', 'changed_images', 'added_RTL_cycles')}))


if __name__ == '__main__':
    main()
