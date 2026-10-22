#!/usr/bin/env python3
"""Export actual LOAD source bytes; fixture outputs are never a source.

capture reads only the small released checkpoint tensors needed for LOAD.
emit runs on the fleet, builds the native RoPE table with the existing golden,
and refuses any source whose hash differs from the actual fixture input hash.
Dynamic Engram gather inputs remain explicit, unexported producer obligations.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

REV = 'dba1be0a40aa45a94ad051997016db3960a90277'
TENSORS = {'q_norm.gain': 'attn.q_norm.weight', 'kv_norm.gain': 'attn.kv_norm.weight',
           'route.bias': 'ffn.gate.bias', 'attend.sink_table': 'attn.attn_sink'}


def capture(snapshot, fixtures, out):
    if snapshot.name != REV:
        raise ValueError('released snapshot revision mismatch')
    wm = json.loads((snapshot / 'model.safetensors.index.json').read_text())['weight_map']
    out.mkdir(parents=True, exist_ok=True)
    rows = {}
    for fixture in fixtures:
        document = json.loads(fixture.read_text())
        layer = document['layer']
        wanted = dict(TENSORS)
        if any(r['tag'] == 'engram.wgt' for r in document['records']['0']):
            wanted.update(_engram_q='engram.q_weight', _engram_k='engram.k_weight')
        for tag, suffix in wanted.items():
            name = f'layers.{layer}.{suffix}'
            file = snapshot / wm[name]
            with file.open('rb') as h:
                n = struct.unpack('<Q', h.read(8))[0]
                meta = json.loads(h.read(n))[name]
                lo, hi = meta['data_offsets']
                h.seek(8 + n + lo)
                raw = h.read(hi - lo)
            dest = f'L{layer:02d}_{tag}.bin'
            (out / dest).write_bytes(raw)
            rows[f'{layer}:{tag}'] = dict(tensor=name, file=dest, shard=file.name,
                 dtype=meta['dtype'], shape=meta['shape'], data_offsets=[lo, hi], sha256=hashlib.sha256(raw).hexdigest())
    (out / 'tensors.json').write_text(json.dumps(dict(revision=REV, tensors=rows), indent=2) + '\n')


def emit(tensors, fixtures, config, out):
    import numpy as np
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import hdc_golden_v41 as V
    source = json.loads((tensors / 'tensors.json').read_text())
    if source['revision'] != REV:
        raise ValueError('captured tensor revision mismatch')
    c = json.loads(config.read_text())
    out.mkdir(parents=True, exist_ok=True)
    records, skipped = [], []
    for fixture in fixtures:
        doc = json.loads(fixture.read_text())
        layer = doc['layer']
        for r in doc['records']['0']:
            if r['op'] != 'DMA.LOAD':
                continue
            tag = r['tag']
            if tag in TENSORS:
                meta = source['tensors'][f'{layer}:{tag}']
                raw = (tensors / meta['file']).read_bytes()
                if hashlib.sha256(raw).hexdigest() != meta['sha256']:
                    raise ValueError('captured tensor changed')
                if tag == 'attend.sink_table':
                    if meta['dtype'] != 'F32':
                        raise ValueError('sink requires actual F32 checkpoint tensor')
                    raw = raw[:4]  # fixture rank0 owns head0
                elif meta['dtype'] != ('BF16' if tag.endswith('.gain') else 'F32'):
                    raise ValueError('checkpoint table dtype mismatch')
                provenance = meta
            elif tag == 'route.one':
                raw = struct.pack('<f', 1.0)
                provenance = dict(source='ds_native.build_tables ONE=np.ones(1,F)')
            elif tag == 'engram.wgt':
                from hdc_golden import mul
                operands, provenance = [], []
                for name in ('_engram_q', '_engram_k'):
                    meta = source['tensors'][f'{layer}:{name}']
                    data = (tensors / meta['file']).read_bytes()
                    if meta['dtype'] != 'BF16' or hashlib.sha256(data).hexdigest() != meta['sha256']:
                        raise ValueError('Engram checkpoint source mismatch')
                    operands.append((np.frombuffer(data, '<u2').astype(np.uint32) << 16).view(np.float32))
                    provenance.append(meta)
                raw = np.asarray(mul(*operands), dtype='<f4').tobytes()
            elif tag == 'kv_rope.table':
                compressed = c['compress_ratios'][layer] > 0
                f = V.rope_freqs(c['rope_head_dim'], c['original_seq_len'] if compressed else 0,
                      c['compress_rope_theta'] if compressed else c['rope_theta'],
                      c['rope_factor'], c['beta_fast'], c['beta_slow'])
                cos, sin = V.rope_cs(f, 1048575)
                raw = np.concatenate([cos, sin]).astype('<f4').tobytes()
                provenance = dict(source='native build_tables rope_cs, rank0, position1048575',
                     config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(), compressed=compressed)
            else:
                skipped.append(dict(layer=layer, record=r['k'], tag=tag,
                                    reason='requires actual dynamic upstream producer; not derived from fixture output'))
                continue
            expected = r['inputs']['A']
            actual = hashlib.sha256(raw).hexdigest()
            if actual != expected['sha256'] or len(raw) != expected['bytes']:
                raise ValueError(f'actual source differs from fixture L{layer}:{tag}: {actual}')
            name = f'L{layer:02d}_k{r["k"]}_{tag}.bin'
            (out / name).write_bytes(raw)
            records.append(dict(layer=layer, record=r['k'], tag=tag, file=name,
                   A=r['desc']['A'], O=r['desc']['O'], sha256=actual, bytes=len(raw), provenance=provenance))
    (out / 'sources.json').write_text(json.dumps(dict(schema='opentallas.dma_load_actual_sources.v1',
          execution_qualified=False, records=records, skipped=skipped,
          note='Source hashes match actual fixture HBM operands. No fixture output used as input.'), indent=2) + '\n')
    print(f'DMA_SOURCE_BYTES_PASS records={len(records)} dynamic_open={len(skipped)}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['capture', 'emit'])
    p.add_argument('--fixtures', type=Path, nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--snapshot', type=Path)
    p.add_argument('--tensors', type=Path)
    p.add_argument('--config', type=Path)
    a = p.parse_args()
    if a.action == 'capture':
        if a.snapshot is None:
            p.error('capture needs --snapshot')
        capture(a.snapshot, a.fixtures, a.out)
    else:
        if a.tensors is None or a.config is None:
            p.error('emit needs --tensors and --config')
        emit(a.tensors, a.fixtures, a.config, a.out)


if __name__ == '__main__':
    main()
