#!/usr/bin/env python3
"""Bounded header/first-block intake for a coarse stage cut, not ROM placement."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def intake(snapshot, owner):
    index_path = snapshot / 'model.safetensors.index.json'
    index_bytes = index_path.read_bytes()
    index = json.loads(index_bytes)['weight_map']
    headers = {}
    layer = owner['layer_owners'][0]
    boundary = owner['cuts'][0]
    assert boundary['layer'] == 0 and boundary['integer_expert_cut'] == 375
    names = ['layers.0.attn.wq_a', 'layers.0.attn.wo_a', 'layers.0.ffn.gate']
    names += [f'layers.0.ffn.experts.{expert}.{matrix}'
              for expert in (374, 375) for matrix in ('w1', 'w2', 'w3')]
    records = []
    for name in names:
        tensors = {}
        for suffix in ('.weight', '.scale'):
            key = name + suffix
            if key not in index:
                if suffix == '.weight':
                    raise ValueError('missing weight: ' + key)
                continue
            filename = index[key]
            path = snapshot / filename
            if filename not in headers:
                with path.open('rb') as source:
                    prefix = source.read(8)
                    length = struct.unpack('<Q', prefix)[0]
                    raw = source.read(length)
                if len(raw) != length:
                    raise ValueError('truncated checkpoint header')
                headers[filename] = (8 + length, json.loads(raw), digest(raw))
            base, header, _ = headers[filename]
            meta = header[key]
            begin, end = meta['data_offsets']
            bits = {'I8': 8, 'F8_E4M3': 8, 'F8_E8M0': 8, 'BF16': 16}[meta['dtype']]
            size = bits // 8
            for dim in meta['shape']:
                size *= dim
            if size != end - begin or base + end > path.stat().st_size:
                raise ValueError('tensor range/shape mismatch: ' + key)
            # Quantized first block is 32 FP8 values or 32 packed FP4 values.
            sample_size = min(end - begin, 16 if meta['dtype'] == 'I8' else
                              32 if suffix == '.weight' else 1)
            with path.open('rb') as source:
                source.seek(base + begin)
                sample = source.read(sample_size)
            if len(sample) != sample_size:
                raise ValueError('truncated tensor sample')
            tensors[suffix[1:]] = dict(tensor=key, shard=filename, dtype=meta['dtype'],
                shape=meta['shape'], absolute_byte_range=[base + begin, base + end],
                row_stride_bytes=meta['shape'][-1] * bits // 8,
                sampled_byte_range=[base + begin, base + begin + sample_size],
                sampled_hex=sample.hex(), sampled_sha256=digest(sample))
        weight = tensors['weight']
        candidate_stage = layer['dense_owner_stage']
        if '.experts.' in name:
            expert = int(name.split('.experts.')[1].split('.')[0])
            matches = [x['stage'] for x in layer['routed_expert_candidate_owners']
                       if x['expert_ids'][0] <= expert <= x['expert_ids'][1]]
            if len(matches) != 1:
                raise ValueError('ambiguous expert owner')
            candidate_stage = matches[0]
        word = None
        if weight['dtype'] in ('I8', 'F8_E4M3'):
            scale = tensors['scale']
            rows, packed_cols = weight['shape']
            logical_cols = packed_cols * (2 if weight['dtype'] == 'I8' else 1)
            expected = [rows if weight['dtype'] == 'I8' else (rows + 31) // 32,
                        logical_cols // 32]
            if scale['dtype'] != 'F8_E8M0' or scale['shape'] != expected:
                raise ValueError('scale layout mismatch: ' + name)
            codes = bytes.fromhex(weight['sampled_hex'])
            exp = int(scale['sampled_hex'], 16)
            nbits = 8 * len(codes)
            word = dict(bits=nbits + 8, first_row_first_block_hex=
                f'{(int.from_bytes(codes, "little") | (exp << nbits)):0{(nbits+8)//4}x}',
                convention='FP4 low nibble first; scale is raw UE8M0 byte, no numerical reorder')
        records.append(dict(name=name, candidate_owner_stage=candidate_stage,
            owner_scope='coarse owner only; TP rank/ROM pair/bank/physical address UNBOUND',
            tensors=tensors, first_quantized_block=word))
    return dict(schema='opentallas.w17.checkpoint_stage_address_intake.v1',
        status='CHECKPOINT_BYTE_OFFSETS_AND_FIRST_BLOCKS_ONLY_NOT_ROM_PLACEMENT',
        checkpoint_revision=snapshot.name, index_sha256=digest(index_bytes),
        shard_header_sha256={k: v[2] for k, v in headers.items()}, records=records,
        payload_pin_scope='Headers and explicit sampled blocks only, not complete weight/scale payloads',
        actual_ROM_mapping=None, executable_stage_program=None, hardware_hop_calendar=None,
        missing_bindings=['Exact TP rank slices and ROM pair/bank/address for full tensor/scale/metadata',
            'Immutable complete stage images and source/data hashes; no dynamic ROM overwrite as product topology',
            'Per-stage executable instruction ranges, tensor phase keys and selected-expert owner lookup',
            'Finite RTL packets for activation, expert output and HC state in golden order',
            'Analytical calendar: payload bits, beats, finite queue depth, backpressure, streaming/serial clocks, replica/fanout/route/area and composed cycles'],
        launch_allowed=False, adopt=False)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    owner = json.loads((ROOT / 'results/arch/v41_stage_owner_product.json').read_text())
    from w17_physical_stage_preflight import preflight
    preflight(ROOT)  # Refuse drift in the W16 coarse owner source basis.
    result = intake(args.snapshot, owner)
    result['source_sha256'] = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in
        (Path(__file__), ROOT/'tools/w17_physical_stage_preflight.py',
         ROOT/'results/arch/v41_stage_owner_product.json')}
    with args.output.open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
