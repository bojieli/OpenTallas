#!/usr/bin/env python3
"""Check source-generated ENGRAM controls against exact F20/F24 serialization.

This checks native compiler -> actual host CSR byte order and descriptor units.
It does not simulate AXI, LCP, issuers or the kernel datapath.
"""
import argparse
import hashlib
import json
from pathlib import Path
from host_program_image import raw_fragment


def check(source, out, profile="legacy19"):
    capacity, limit, guard = {"legacy19": (2432, 2424, 1218), "slot160_21": (2688, 2569, 1346), "slot160_21_drain5": (2688, 2574, 1346), "slot160_21_ordered_drain5": (2688, 2091, 1346)}[profile]
    images = []
    for path in sorted(source.glob('layer*/n*.hex')):
        words = [int(line, 16) for line in path.read_text().splitlines() if line.strip()]
        if len(words) != capacity:
            raise ValueError(f'{path}: {profile} requires {capacity} operations')
        image = dict(target=120, encoding='raw_control256', native_profile=profile, programme=dict(
            start=dict(base=0, limit=limit, loops=1),
            configuration_writes=[dict(addr=pc, data=f'{word:064x}') for pc, word in enumerate(words)]))
        fragment = raw_fragment(image)
        replay, current, pieces = {}, None, []
        for operation in fragment['axi_writes']:
            if operation.get('address') == 0xf20:
                if pieces: raise ValueError('Frame select interrupted word')
                if operation['data'] & 255 != 120: raise ValueError('Target identity changed')
                current = operation['data'] >> 8
            elif operation.get('address') == 0xf24:
                pieces.append(operation['data'])
                if len(pieces) == 8:
                    replay[current] = sum(value << (32*index) for index, value in enumerate(pieces))
                    pieces = []
            elif operation.get('address') == 0xf28:
                if operation['data'] != limit << 12: raise ValueError('Descriptor cycle units changed')
        if [replay[pc] for pc in range(capacity)] != words:
            raise ValueError('Raw control payload or half-order changed')
        if fragment['launch_guard_core_edges'] != guard: raise ValueError('Descriptor scan guard changed')
        payload = json.dumps(fragment, sort_keys=True, separators=(',', ':')).encode()
        images.append(dict(source=str(path.relative_to(source)), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           host_fragment_sha256=hashlib.sha256(payload).hexdigest(), operations=2432, executing_limit=limit,
                           axi_operations=len(fragment['axi_writes']), target=120, physical_scope='one independent node image per physical rank; not eighteen consumers sharing one target'))
    if len(images) != 18: raise ValueError('Expected actual nine nodes at two Engram layers')
    receipt = dict(schema='opentallas.hbm.engram-native-host-roundtrip.v1', result='PASS', images=images,
                   exact_raw_operations=18*capacity, payload_bits=238, frame_bits=256,
                   native_profile=profile, native_banks=21 if profile != 'legacy19' else 19, descriptor_guard_edges=guard, source_issuer_commit='79037c152', target_contract='program_target_map.v2',
                   scope='Actual source compiler controls -> typed raw fragment -> exact CSR frame byte-order roundtrip only; full AXI/LCP/native issuer/kernel composition remains open')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('out', type=Path)
    parser.add_argument('--profile', choices=['legacy19', 'slot160_21', 'slot160_21_drain5', 'slot160_21_ordered_drain5'], default='legacy19')
    args = parser.parse_args(); result = check(args.source, args.out, args.profile)
    print(f"PASS images={len(result['images'])} exact_raw_operations={result['exact_raw_operations']}")
