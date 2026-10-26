#!/usr/bin/env python3
"""53-bit seq-host KS codec: {start, user10, token21, position21}.

This describes the existing input wire. It does not supply a production HOST
descriptor producer, stage address, rank field, or a qualified launch epoch.
"""
import argparse
import hashlib
import json
from pathlib import Path


def encode(*, user, token, position):
    for name, value, width in [('user', user, 10), ('token', token, 21), ('position', position, 21)]:
        if type(value) is not int or not 0 <= value < 1 << width:
            raise ValueError(f'{name} requires unsigned {width}-bit integer')
    return (1 << 52) | (user << 42) | (token << 21) | position


def decode(word):
    if type(word) is not int or not 0 <= word < 1 << 53 or word >> 52 != 1:
        raise ValueError('KS requires exactly the active 53-bit seq-host descriptor')
    return dict(user=(word >> 42) & 1023, token=(word >> 21) & ((1 << 21)-1),
                position=word & ((1 << 21)-1))


def validate(word, *, user, token, position):
    expected = dict(user=user, token=token, position=position)
    if decode(word) != expected or encode(**expected) != word:
        raise ValueError('KS decoded user/token/position differs from intended descriptor')
    return expected


def fixture_word(meta, *, user, supplied=None):
    fields = dict(user=user, token=meta['token'], position=meta['position'])
    word = encode(**fields) if supplied is None else supplied
    validate(word, **fields)
    return word


def source_witness(path):
    raw = Path(path).read_bytes()
    required = ['.job_v(ks_q[52])', '.job_user(ks_q[51:42])',
                '.job_pos(ks_q[20:0])', '.job_tok(ks_q[41:21])']
    lines = [dict(line=i, text=line.strip()) for i, line in enumerate(raw.decode().splitlines(), 1)
             if any(text in line for text in required)]
    if not all(any(text in line['text'] for line in lines) for text in required):
        raise ValueError('selected seq-host source does not witness the codec bit fields')
    return dict(path=str(Path(path).resolve()), sha256=hashlib.sha256(raw).hexdigest(), statements=lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture-meta', type=Path, required=True)
    p.add_argument('--user', type=int, required=True, help='explicit incoming HOST user; absent from fixture metadata')
    p.add_argument('--seq-host-source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('preserve existing descriptor receipt; use a fresh output')
    meta = json.loads(a.fixture_meta.read_text())
    fields = dict(user=a.user, token=meta['token'], position=meta['position'])
    word = encode(**fields); validate(word, **fields)
    old = (1 << 52) | (fields['user'] << 42) | (fields['position'] << 21) | fields['token']
    r = dict(schema='opentallas.s81.ks_descriptor.v1', status='SOURCE_CODEC_ONLY_NOT_EXECUTED',
             fields=fields, word53=f'{word:014x}', decoded=decode(word),
             fixture_meta_sha256=hashlib.sha256(a.fixture_meta.read_bytes()).hexdigest(),
             user_provenance='explicit harness input; no executable production descriptor producer proved',
             fixture_rank=meta.get('rank'), fixture_tp=meta.get('tp'), rank_carried_in_KS=False,
             stage_address_carried_in_KS=False, source=source_witness(a.seq_host_source),
             superseded_swapped_word=dict(word53=f'{old:014x}', decoded=decode(old),
                 status='FAILED_DESCRIPTOR_IDENTITY_UNEXECUTED',
                 reason='inherited token/position order was reversed; not valid fixture provenance'),
             runtime_provenance_qualified=False, launch_epoch=None, full_stage=False, full_token=False)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(r, indent=1)+'\n')
    print('KS_SOURCE_CODEC', r['word53'], fields, 'not a runtime HOST/launch proof')


if __name__ == '__main__':
    main()
