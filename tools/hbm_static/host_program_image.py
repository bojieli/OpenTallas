#!/usr/bin/env python3
"""Build actual F-window host writes from complete, typed native programmes.

This serializes programmes; it does not qualify arithmetic, timing or kernel
coverage. The caller supplies the complete required-target census explicitly.
"""
import argparse
import json
from pathlib import Path


def integer(value):
    return int(value, 0) if isinstance(value, str) else int(value)


def build(spec):
    required = {integer(t) for t in spec['required_targets']}
    if not {0, 1, 2, 3} <= required:
        raise ValueError('Actual host launch requires programmes for all four VM quadrants')
    images = {integer(i['target']): i for i in spec['images']}
    if len(images) != len(spec['images']):
        raise ValueError('Duplicate programme target')
    if required != set(images):
        raise ValueError(f'Required target/image mismatch: missing={sorted(required-set(images))}, extra={sorted(set(images)-required)}')
    writes, manifest = [], []
    for target in sorted(images):
        image = images[target]
        if not (target in range(4) or 16 <= target <= 255):
            raise ValueError('Target is outside the actual direct-VM/extended-engine map')
        pcw = integer(image['PCW'])
        payload = integer(image['payload_bits'])
        if not 8 <= pcw <= 12 or not 1 <= payload <= 233-pcw:
            raise ValueError('Protected programme payload/PC does not fit its actual word')
        if target < 4 and pcw != 10:
            raise ValueError('Direct VM programme SRAM has exactly ten address bits')
        programme = image['programme']
        start = {k: integer(programme['start'][k]) for k in ('base', 'limit', 'loops')}
        if not (0 <= start['base'] < start['limit'] <= 1 << pcw and 1 <= start['loops'] <= 65535):
            raise ValueError('Programme range/loop count exceeds actual target capacity')
        words = {}
        for item in programme['configuration_writes']:
            address = integer(item['addr'])
            data = item['data']
            # Native emitters write exactly 64 hex digits without a prefix.
            word = int(data, 16) if isinstance(data, str) else int(data)
            if address in words or not 0 <= address < 1 << pcw or not 0 <= word < 1 << 256:
                raise ValueError('Duplicate/out-of-range native programme word')
            pc_lo = 234-pcw
            if word >> 240 != 0xc7a1 or (word >> pc_lo) & ((1 << pcw)-1) != address:
                raise ValueError('Programme magic/global-PC identity mismatch')
            allowed = ((1 << payload)-1) | (((1 << pcw)-1) << pc_lo) | (0xffff << 240)
            if word & ~allowed:
                raise ValueError('Programme reserved bits are nonzero')
            words[address] = word
        if not set(range(start['base'], start['limit'])) <= set(words):
            raise ValueError('Programme contains a hole in its executing range')
        select, data_reg, range_reg, loop_reg = (0xf00, 0xf04, 0xf08, 0xf0c) if target < 4 else (0xf20, 0xf24, 0xf28, 0xf2c)
        last = None
        for address, word in sorted(words.items()):
            if last is None or address != last+1:
                value = (address << (2 if target < 4 else 8)) | target
                writes.append(dict(address=select, data=value))
            for piece in range(8):
                writes.append(dict(address=data_reg, data=(word >> (32*piece)) & 0xffffffff))
            last = address
        range_data = (start['limit'] << (10 if target < 4 else 12)) | start['base']
        writes += [dict(address=range_reg, data=range_data), dict(address=loop_reg, data=start['loops'])]
        manifest.append(dict(target=target, PCW=pcw, payload_bits=payload, words=len(words), start=start,
                             first_programme_after_LCP71=6 if target < 4 else 8))
    # This is the existing real loader/CP doorbell address, after configuration.
    writes.append(dict(address=0xc10, data=integer(spec.get('doorbell', 1))))
    return dict(schema='opentallas.hbm.actual-host-program-image.v1', kernel=spec['kernel'],
                required_targets=sorted(required), targets=manifest, axi_writes=writes,
                write_strobes=15,
                qualification='Configuration sequence only; actual source/engine/transport/physical/layer gates remain required.',
                unsupported='Wide raw COLL/DMA controllers need their own proven 256b frame assembler; protected payloads are never silently truncated.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(build(json.loads(args.spec.read_text())), indent=2)+'\n')


if __name__ == '__main__':
    main()
