#!/usr/bin/env python3
"""Emit bounded real HEAD37 loader rows for an unadopted monitored source.

Uses the existing native table ABI and completed pidx16 stage as its baseline.
No full physical mask volume, caller, calendar date or active cache is written.
"""
import argparse
import hashlib
import json
from pathlib import Path
import programme_store as P


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(stage, baseline):
    monitor = stage.get('native_head_monitor')
    if stage.get('stage') != 37 or baseline.get('stage') != 37:
        raise ValueError('actual HEAD37 stage required')
    if monitor != dict(slice=0, apply_pidx=16, monitor_pidx=17,
                       extra_pairs=0, extra_cycles=0):
        raise ValueError('requires explicit unadopted slice0 monitor source')
    if sorted(s['slice'] for s in stage['slices']) != list(range(12)):
        raise ValueError('all twelve actual native slices required')
    before = {s['slice']: s for s in baseline['slices']}
    images = []
    differences = []
    for sl in sorted(stage['slices'], key=lambda s: s['slice']):
        sid = sl['slice']
        old = before[sid]
        if sl['btab'] != old['btab'] or sl['crom'] != old['crom']:
            raise ValueError('genuine gain/BTAB differs from completed source')
        if len(sl['btab']) != P.HEAD_BTAB_COUNTS[sid] or len(sl['crom']) != P.HEAD_CROM_COUNTS[sid]:
            raise ValueError('actual stage family ownership changed')
        if len(sl['prog_users']) != 4:
            raise ValueError('four certified user payloads required')
        words = [0] * P.STRIDE
        for user, records in enumerate(sl['prog_users']):
            if len(records) != 1 or records[0]['addr'] != 8:
                raise ValueError('actual native pair8 source required')
            rec, prior = records[0], old['prog_users'][user][0]
            payload, prior_payload = int(rec['payload_hex'], 16), int(prior['payload_hex'], 16)
            lowmask = (1 << 512) - 1
            if prior_payload >> 512 or payload & lowmask != prior_payload:
                raise ValueError('original native apply instruction changed')
            expected = prior_payload | (prior_payload << 512 if sid == 0 else 0)
            if payload != expected:
                raise ValueError('monitor source is not exact existing upper-pair copy')
            if payload != prior_payload:
                differences.append(dict(slice=sid, user=user, row=3816 + user * P.PROG,
                                        pidx=17 + 128 * user, added_pairs=0, added_cycles=0))
            words[user * P.PROG] = P.encode(3, rec['addr'], rec['payload_hex'], head=True)
        for kind, start, cap, records in [(2, 4 * P.PROG, P.HEAD_BTAB, sl['btab']),
                                         (1, 4 * P.PROG + P.HEAD_BTAB, P.HEAD_CROM, sl['crom'])]:
            if len(records) > cap:
                raise ValueError('stage exceeds native fixed reservation')
            for i, rec in enumerate(records):
                words[start+i] = P.encode(kind, rec['addr'], rec['payload_hex'], head=True)
        images.append(words)
    if len(differences) != 4 or (P.STRIDE, P.PROG) != (106, 6):
        raise ValueError('monitor delta or native storage ABI changed')
    return images, differences


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('stage', 'baseline', 'out'):
        p.add_argument('--'+key, type=Path, required=True)
    a = p.parse_args()
    images, differences = emit(json.loads(a.stage.read_text()), json.loads(a.baseline.read_text()))
    a.out.mkdir(parents=True, exist_ok=False)
    for sid, words in enumerate(images):
        (a.out/f'slice{sid}_stage106.hex').write_text(''.join(f'{w:0260x}\n' for w in words))
        for user in range(4):
            addresses = P.read_rows(37, user, head_stage37=True)
            raw = [words[r-3816] for r in addresses]
            relocated = [P.relocate_word(w, user, btab_compact=True, head=True) for w in raw]
            for label, values in [('read88', raw), ('write88', relocated)]:
                (a.out/f'slice{sid}_user{user}_{label}.hex').write_text(''.join(f'{w:0260x}\n' for w in values))
    receipt = dict(status='SOURCE_FIXTURE_NOT_ACTIVATED_NOT_EXECUTED', stage=37,
                   stage_rows=[3816, 3922], rows_per_slice=106, reads_per_user=88,
                   slices=12, users=4, differences_from_completed_pidx16=differences,
                   raw_read='exact fixed native store window, includes real zero/NOP reservations',
                   runtime_write='existing programme_store.relocate_word native compact HEAD ABI; payload unchanged',
                   monitor='slice0 candidate only; earliest global producer and caller remain unadopted',
                   source_sha256={str(x): sha(x) for x in [a.stage, a.baseline, Path(P.__file__)]},
                   output_sha256={x.name: sha(x) for x in a.out.glob('*.hex')},
                   scope='bounded input fixture for actual native table loader; no full masks, programme dates, physical phase or arithmetic claim')
    (a.out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(status=receipt['status'], slices=12, rows=106, reads=88,
                          changed_native_words=len(differences), output_bytes=sum(x.stat().st_size for x in a.out.iterdir()))))


if __name__ == '__main__':
    main()
