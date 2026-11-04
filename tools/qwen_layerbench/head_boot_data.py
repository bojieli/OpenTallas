#!/usr/bin/env python3
"""Lower genuine HEAD scales into the resident native BTAB window.

This does not synthesize missing native final-norm instructions or choose their
CROM addresses. Final-norm weights are exported as logical FP32 pairs only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
import dv_lower as D
import dv_lower_mat as M


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def head_tables(meta, scale_path, own):
    if (meta['tp'], meta['groups'], meta['rows']) != (8, 3072, 18992):
        raise ValueError('requires released TP8/G3072 HEAD geometry')
    if sha(scale_path) != meta['image_sha256']['matrix_scale_bf16.hex']:
        raise ValueError('HEAD scale image digest mismatch')
    rows = Path(scale_path).read_text().splitlines()
    if len(rows) != meta['scale_words'] or any(len(r) != 64 for r in rows):
        raise ValueError('HEAD scale bank shape mismatch')
    scales = [(int(w, 16) >> (16*j)) & 0xffff for w in rows for j in range(16)][:meta['rows']]
    if len(scales) != meta['rows']:
        raise ValueError('missing HEAD scale rows')
    layout = M.btab_layout(own)['lm_head']
    records = []
    for sid, entries in sorted(layout.items()):
        words = {}
        for e in entries:
            for j in range(8):
                address = e['sbase'] + j
                if address not in range(72, 272) or address in words:
                    raise ValueError('HEAD BTAB overlap or window violation')
                row0 = 128*e['block'] + 16*j
                # Native btab_stream pads non-vocabulary rows with zero. The
                # matrix engine bank pads with 1.0; never copy that padding.
                words[address] = sum((scales[r] if r < len(scales) else 0) << (16*k)
                                     for k, r in enumerate(range(row0, row0+16)))
        for a in sorted({a//4*4 for a in words}):
            payload = sum(words.get(a+j, 0) << (256*j) for j in range(4))
            native = payload | (1 << 1024) | (2 << 1025) | (a << 1027)
            records.append(dict(slice=sid, kind=2, addr=a, payload_hex=f'{payload:0256x}',
                                native_word_hex=f'{native:0263x}'))
    return records, scales


def final_norm(snapshot):
    index = json.loads((snapshot/'model.safetensors.index.json').read_text())['weight_map']
    path = snapshot/index['model.norm.weight']
    with path.open('rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]
        header = json.loads(f.read(n))
        tensor = header['model.norm.weight']
        if tensor['shape'] != [4096] or tensor['dtype'] not in ('BF16', 'F32'):
            raise ValueError('unexpected final norm tensor contract')
        lo, hi = tensor['data_offsets']
        width = 2 if tensor['dtype'] == 'BF16' else 4
        if hi-lo != width*4096:
            raise ValueError('final norm tensor length mismatch')
        f.seek(8+n+lo)
        data = f.read(hi-lo)
    if len(data) != hi-lo:
        raise ValueError('truncated final norm')
    values = struct.unpack('<4096H' if width == 2 else '<4096I', data)
    bits = [v << 16 for v in values] if width == 2 else list(values)
    return bits, dict(tensor='model.norm.weight', shard=path.name, dtype=tensor['dtype'],
                      source_tensor_sha256=hashlib.sha256(data).hexdigest())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--head-bank', type=Path, required=True)
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--plan', default=D.PLAN)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    meta = json.loads((a.head_bank/'head_rom.json').read_text())
    plan = json.loads((D.ROOT/a.plan).read_text())
    for key in ('rows', 'columns', 'split', 'rounds', 'tiles_per_round'):
        if meta['geometry'][key] != plan['head_geometry'][key]:
            raise ValueError(f'selected HEAD plan differs: {key}')
    if a.snapshot.name != meta['checkpoint_revision']:
        raise ValueError('snapshot revision differs from HEAD matrix source')
    records, scales = head_tables(meta, a.head_bank/'matrix_scale_bf16.hex', D.ownership(a.plan, 's8'))
    norm, source = final_norm(a.snapshot)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/'head_btab.json').write_text(json.dumps(records, indent=2)+'\n')
    # Same low-FP32/high-zero logical representation as the existing
    # qwen_o4_fulltoken_binding_w12.write_final_norm producer.
    (a.out/'head_final_norm_crom.hex').write_text(''.join(f'{v:016x}\n' for v in norm))
    result = dict(schema='opentallas.qwen.head-boot-data.v1', stage=37, rank=meta['die'],
                  status='PARTIAL', native_btab_records=len(records), btab_window=[72,272],
                  btab_slices=sorted({r['slice'] for r in records}), norm_logical_words=len(norm),
                  norm_source=source, checkpoint_revision=meta['checkpoint_revision'],
                  native_head_programme='NOT_LOWERED', native_norm_crom_addresses='NOT_ASSIGNED',
                  boot_transport='NOT_INSTALLED', activation_calendar='NOT_EMITTED',
                  source_sha256={'head_rom.json':sha(a.head_bank/'head_rom.json'),
                                 'matrix_scale_bf16.hex':sha(a.head_bank/'matrix_scale_bf16.hex'),
                                 'selected_plan':sha(D.ROOT/a.plan)},
                  claim_boundary='Genuine native shared BTAB payload and logical final norm only; no native HEAD programme or stage37 loader closure.')
    (a.out/'head_boot_data.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    main()
