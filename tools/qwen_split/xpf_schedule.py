#!/usr/bin/env python3
"""Derive pre-producer arm records from actual instruction bits, fail closed.

Records are schedule data, not proof that RTL is integrated. A live-in has no
producer in this image and MUST be armed in its real preceding stage. The
native attention op is an explicit binary32 VM writer even though its old
ME instruction used packed S/M output semantics. Its effects must therefore
be supplied from the source-bound native lowering receipt.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdc_qwen_fullshape_isa_w12 as ISA


def descriptor(f):
    fields = [('me_xbase', 24, 1), ('me_xcs', 12, 25),
              ('me_xks', 12, 37), ('me_split', 4, 49),
              ('me_k', 18, 53), ('me_round', 1, 71)]
    value = 1
    for name, width, offset in fields:
        v = f[name]
        if not 0 <= v < 1 << width:
            raise ValueError(f'{name}={v} exceeds the actual xpf width{width}')
        value |= v << offset
    return f'{value:018x}'


def su_writes(f):
    if f['unit'] != 2 or f['dst'] != 1:
        return set()
    if f['su_d_nin'] or f['d_d']:
        raise ValueError('dynamic SU writer requires resolved production position')
    return {f['d_base'] + o*f['d_so'] + i*f['d_si']
            for o in range(f['su_nout']) for i in range(f['su_nin'])}


def schedule(raw, external_writes=()):
    words = [ISA.decode_instruction(int(w, 16)) for w in raw.decode().split()]
    writers = {}
    external = {}
    receipts = []
    for effect in external_writes:
        pc = effect['producer_pc']
        if not 0 <= pc < len(words) or words[pc]['unit'] != effect['producer_unit']:
            raise ValueError('external producer does not bind actual instruction unit/PC')
        if not effect.get('source'):
            raise ValueError('external VM effect needs real native source attribution')
        source = Path(effect['source'])
        if not source.is_file():
            raise ValueError('external native producer source does not exist')
        f = words[pc]
        if f['unit'] != 1 or not f['me_wsrc'] or effect['base'] != f['me_obase']*16 or effect['count'] != f['me_nout']:
            raise ValueError('native VM effect differs from the actual instruction output range')
        receipts.append(dict(effect, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
        external.setdefault(pc, set()).update(range(effect['base'], effect['base']+effect['count']))
    records = []
    gaps = []
    for pc, f in enumerate(words):
        if f['unit'] == 1 and not f['me_wsrc']:
            if f['me_xjs'] or f['me_d_xbase'] or f['me_d_k']:
                raise ValueError('unsupported compute operand: xjs or unresolved dynamic address/count')
            required = {f['me_xbase'] + c*f['me_xcs'] + k*f['me_xks']
                        for c in range(1 << f['me_split']) for k in range(f['me_k'])}
            missing = required - writers.keys()
            producers = sorted({writers[a] for a in required if a in writers})
            record = dict(consumer_pc=pc, consumer_unit=1, xpf_hex=descriptor(f),
                          x_elements=len(required), producer_pcs=producers,
                          arm_before_pc=min(producers) if producers and not missing else None,
                          producer_unit=words[min(producers)]['unit'] if producers and not missing else None)
            if missing:
                gaps.append(dict(consumer_pc=pc, live_in_elements=len(missing),
                                 first_live_in=min(missing), last_live_in=max(missing),
                                 required_action='arm in actual preceding producer stage or measured VM replay'))
            # Same X may serve multiple chunks without fresh writes. Two-epoch
            # consumption cannot manufacture the later epoch's fill from it.
            if producers and any(r['producer_pcs'] == producers for r in records):
                gaps.append(dict(consumer_pc=pc, required_action='explicit retained-epoch reuse or real replay; no second unfilled arm'))
            records.append(record)
        for address in su_writes(f) | external.get(pc, set()):
            writers[address] = pc
    return dict(schema='opentallas.qwen-xpf-producer-schedule.v1',
                program_sha256=hashlib.sha256(raw).hexdigest(), records=records,
                external_effects=receipts, unresolved=gaps,
                status='PRECEDING_STAGE_REQUIRED' if gaps else 'LOCAL_PRODUCERS_RESOLVED',
                claim='Static instruction-bound arm records only; relay latency, table loading, epoch ownership and release guard require RTL composition.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--program', type=Path, required=True)
    p.add_argument('--external-effects', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    effects = json.loads(a.external_effects.read_text()) if a.external_effects else []
    result = schedule(a.program.read_bytes(), effects)
    a.out.write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'])
    return 2 if result['unresolved'] else 0


if __name__ == '__main__':
    sys.exit(main())
