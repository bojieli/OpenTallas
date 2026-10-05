#!/usr/bin/env python3
"""Checkpoint-backed vectors for one shared HBROM compute tile (software only).

Golden results are separate files, never ROM/activation runtime inputs. Physical
words use hbrom_allocator's four-stream interleaved FP4 layout. --rows is required
until the architectural allocator chooses a full cluster shard. Activation input
is explicit .npy, or labelled deterministic synthetic; weights are checkpoint bits.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import dsrom_s82_payload_interface as P
import hbrom_allocator as A
import hdc_golden as G
import hdc_golden_v41 as V
import rtl_gpu_sm_exact as S

DEFAULT_TENSORS = ['layers.0.ffn.experts.0.w1.weight',
                   'layers.0.ffn.experts.1.w2.weight',
                   'layers.0.attn.wq_a.weight', 'layers.0.attn.wq_b.weight',
                   'layers.0.attn.wo_a.weight', 'layers.0.attn.wo_b.weight', 'head.weight']


def checkpoint_rows(source, name, ids):
    """Read only requested source rows/scales; never materialize whole tensors."""
    _, _, meta = source.descriptor(name)
    dtype = meta['dtype']; shape = meta['shape']
    if len(shape) != 2 or not ids or min(ids) < 0 or max(ids) >= shape[0]:
        raise ValueError('source row bounds/shape')
    if dtype not in ('I8', 'F8_E4M3', 'BF16'):
        raise ValueError('unsupported weight dtype')
    width = 2 if dtype == 'BF16' else 1
    raw = b''.join(source.raw(name, row*shape[1]*width, shape[1]*width) for row in ids)
    codes = np.frombuffer(raw, dtype='<u2' if width == 2 else np.uint8).reshape(len(ids), shape[1])
    scales = None; scale_raw = b''
    if dtype == 'BF16':
        fmt = 'bf16'; weights = G.from_bits(codes.astype(np.uint32) << 16)
    else:
        scname = name.removesuffix('.weight') + '.scale'
        _, _, sm = source.descriptor(scname)
        if sm['dtype'] != 'F8_E8M0': raise ValueError('expected released UE8M0 scales')
        scale_raw = b''.join(source.raw(scname, (r if dtype == 'I8' else r//32)*sm['shape'][1],
                                       sm['shape'][1]) for r in ids)
        scales = np.frombuffer(scale_raw, dtype=np.uint8).reshape(len(ids), sm['shape'][1])
        if dtype == 'I8':
            codes = np.stack([codes & 15, codes >> 4], axis=-1).reshape(len(ids), -1)
            fmt = 'fp4'; q = V.E2M1[codes]
        else:
            fmt = 'fp8'; q = V.E4M3[codes]
        weights = V.Q8(q.astype(np.float64), scales.astype(np.int64)-127)
        if name.endswith('attn.wo_a.weight'):
            weights = G.to_bf16(weights.dense())
            codes = S.bf16_bits(weights); scales = None; fmt = 'bf16'
    return dict(format=fmt, codes=codes, scales=scales, weights=weights,
                source_sha256=hashlib.sha256(raw+scale_raw).hexdigest(),
                source_dtype=dtype, source_shape=shape)


def golden_accumulators(weights, x, fmt):
    """Independent golden math; does not decode physical ROM or SM line outputs."""
    V.set_arith('chunk8')
    if fmt == 'bf16': return V.csum(G.mul(weights, G.to_bf16(x)[None, :]))
    xq, xe = V.quant_fp8(x)
    terms = [np.ldexp((weights.q[:, b*32:(b+1)*32] @ xq[b*32:(b+1)*32]).astype(np.float32),
                     weights.e[:, b]+xe[b]).astype(np.float32)
             for b in range(weights.q.shape[1]//32)]
    return V.csum(np.stack(terms, axis=-1))


def activation_fragments(x, fmt, groups, depth=128):
    lanes = {'fp4':8, 'fp8':4, 'bf16':64}[fmt]
    if groups*8 > depth: raise ValueError('fullK activation store capacity')
    if fmt == 'bf16': codes = S.bf16_bits(x)
    else:
        q, exp = V.quant_fp8(x); codes = S._codes()[0](q)
    words = []
    for addr in range(depth):
        group, step = divmod(addr, 8); word = 0
        if group < groups:
            for lane in range(lanes):
                k = A.code_coordinate(fmt, group, step, lane)
                if k >= len(x): continue
                if fmt == 'bf16': word |= int(codes[k]) << (8*266+lane*16)
                else:
                    field = sum(int(codes[k+j]) << (8*j) for j in range(32))
                    field |= (int(exp[k//32]) & 1023) << 256
                    word |= field << (lane*266)
        words.append(word)
    return words


def emit_case(source, name, ids, out, bankgroup, x=None, seed=20261005,
              layout_mode='compact', output_rounding='auto', record_offset=0, activation_group=None):
    V.set_arith('chunk8')
    payload = checkpoint_rows(source, name, ids)
    fmt = payload['format']; codes = payload['codes']; k = codes.shape[1]
    if k % 32 and fmt != 'bf16': raise ValueError('quantized K block alignment')
    if not 0 < len(ids) <= 4096: raise ValueError('RMAX capacity')
    geom = A.row_geometry(fmt, k, layout_mode)
    if x is None:
        x = G.to_bf16(np.random.default_rng(seed).normal(size=k).astype(np.float32))
        origin = 'synthetic_deterministic_activation_real_checkpoint_weights'
    else:
        x = np.asarray(x, dtype=np.float32)
        if x.shape != (k,): raise ValueError('activation must match full logical K')
        origin = 'caller_supplied_activation_real_checkpoint_weights'
    if not np.all(np.isfinite(x)): raise ValueError('nonfinite activation')
    expected = golden_accumulators(payload['weights'], x, fmt)
    if not np.all(np.isfinite(expected)): raise ValueError('golden nonfinite')
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    physical = []; addresses = {}; virtual = []; line_addresses = []
    for row in range(len(ids)):
        for g in range(geom['groups']):
            for t in range(8):
                if g*8+t not in geom['physical_steps']: continue
                words = A.encode_record(fmt,k,g,t,lambda p: int(codes[row,p]),
                                        None if payload['scales'] is None else lambda b: int(payload['scales'][row,b]))
                addresses[row,g,t] = len(physical); physical.append(words)
    for r,g,t in S.issue_order(len(ids),geom['groups'],8,True):
        words = A.encode_record(fmt,k,g,t,lambda p: int(codes[r,p]),
                                None if payload['scales'] is None else lambda b: int(payload['scales'][r,b]))
        virtual.append(A.swizzle(fmt,words)); line_addresses.append(addresses.get((r,g,t),-1))
    # Each local bankgroup is four streams with two alternating 4096-row macros.
    # Large row shards may require consecutive physical bankgroups.
    if record_offset<0 or record_offset>=8192:raise ValueError('record offset')
    image_groups = (record_offset+len(physical)+8191)//8192
    for bg in range(image_groups):
        entries = [(record_offset+r-bg*8192,words) for r,words in enumerate(physical) if bg*8192<=record_offset+r<(bg+1)*8192]
        for stream in range(4):
            for parity in range(2):
                locations = {((r//16)*8+r%8): words[stream] for r,words in entries if (r//8)%2 == parity}
                vals = [locations.get(addr,0) for addr in range(max(locations,default=-1)+1)]
                (out/f'rom_g{bankgroup+bg}_s{stream}_p{parity}.hex').write_text(''.join(f'{v:069x}\n' for v in vals))
    (out/'lines_reference.hex').write_text(''.join(f'{v:0272x}\n' for v in virtual))
    (out/'line_address.hex').write_text(''.join(f'{v & 0xffffffff:08x}\n' for v in line_addresses))
    (out/'x.hex').write_text(''.join(f'{v:0788x}\n' for v in activation_fragments(x,fmt,geom['groups'])))
    np.save(out/'activation.npy',x)
    (out/'cfg.hex').write_text(''.join(f'{v:08x}\n' for v in [len(ids),8,geom['groups'],{'bf16':0,'fp8':1,'fp4':2}[fmt],len(virtual),1,0,0]))
    if output_rounding == 'auto': output_rounding = 'fp32' if name=='head.weight' or name.endswith('ffn.gate.weight') else 'bf16'
    final = G.to_bf16(expected) if output_rounding=='bf16' else expected
    for path, values in [('expected_fp32.hex',expected),('expected_output.hex',final)]:
        (out/path).write_text(''.join(f'{int(v):08x}\n' for v in G.bits(values)))
    files = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    result = dict(schema='opentallas.hbrom.vectors.v1',tensor=name,source_rows=ids,logical_K=k,
                  format=fmt,geometry=geom,bankgroup_base=bankgroup,bankgroups=image_groups,
                  physical_base_record=bankgroup*8192+record_offset,activation_group=activation_group,
                  physical_records=len(physical),issued_records=len(virtual),activation_origin=origin,
                  output_rounding=output_rounding,source_sha256=payload['source_sha256'],
                  source_dtype=payload['source_dtype'],source_shape=payload['source_shape'],
                  checkpoint_revision=P.SNAPSHOT,weight_nonzero_codes=int(np.count_nonzero(codes)),
                  weight_distinct_codes=int(np.unique(codes).size),
                  scale_distinct_codes=None if payload['scales'] is None else int(np.unique(payload['scales']).size),
                  golden='hdc_golden_v41.csum chunk8, FP32 before consumer rounding',files_sha256=files,
                  runtime_inputs=['rom_g*_s*_p*.hex','line_address.hex','x.hex','cfg.hex'],
                  checker_only=['expected_fp32.hex','expected_output.hex','lines_reference.hex'],
                  scope='One tile fullK row shard; no whole-model exactness or physical qualification claim')
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint',type=Path,default=P.DEFAULT_CHECKPOINT)
    ap.add_argument('--tensor',action='append',help='Repeat for multiple sequential operations; default representative suite')
    ap.add_argument('--rows',type=int,help='Explicit row count; otherwise --owners required')
    ap.add_argument('--owners',type=int,help='Full-shape cyclic row ownership; all rows belonging to --row-start owner')
    ap.add_argument('--six-experts',action='store_true',help='Exercise experts0..5 w1/w3/w2 on the same compute plus dense/head suite')
    ap.add_argument('--row-start',type=int,default=0);ap.add_argument('--row-stride',type=int,default=1)
    ap.add_argument('--bankgroup-base',type=int,default=0)
    ap.add_argument('--layout-mode',choices=['padded','compact'],default='compact')
    ap.add_argument('--activation',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if (a.rows is None)==(a.owners is None):ap.error('choose exactly one of --rows or --owners')
    if (a.rows is not None and a.rows<=0) or (a.owners is not None and a.owners<=0) or a.row_stride<=0 or min(a.row_start,a.bankgroup_base)<0:ap.error('invalid row/bankgroup geometry')
    source=P.Checkpoint(a.checkpoint);cases=[];bg=a.bankgroup_base
    try:
        names=a.tensor or ([f'layers.0.ffn.experts.{e}.{w}.weight' for e in range(6) for w in ['w1','w3','w2']]+DEFAULT_TENSORS[2:] if a.six_experts else DEFAULT_TENSORS)
        for name in names:
            ids=list(range(a.row_start,source.descriptor(name)[2]['shape'][0],a.owners)) if a.owners else [a.row_start+j*a.row_stride for j in range(a.rows)]
            grouped=name.endswith('attn.wo_a.weight')
            partitions=[(g,[r for r in ids if g*1024<=r<(g+1)*1024]) for g in range(8)] if grouped else [(None,ids)]
            offset=0
            for group,owned in partitions:
                if not owned:continue
                x=None if a.activation is None else np.load(a.activation)
                if grouped and x is not None:
                    if x.shape!=(8,4096):raise ValueError('wo_a activation requires eight distinct group rows [8,4096]')
                    x=x[group]
                result=emit_case(source,name,owned,a.out/f'op{len(cases):02d}',bg,x,
                                 seed=20261005+(group or 0),layout_mode=a.layout_mode,
                                 record_offset=offset,activation_group=group)
                cases.append(result)
                if grouped:offset+=result['physical_records']
                else:bg+=result['bankgroups']
            if grouped:bg+=(offset+8191)//8192
    finally:source.close()
    (a.out/'campaign.json').write_text(json.dumps(dict(schema='opentallas.hbrom.vector_campaign.v1',
       sequential_same_compute=True,cases=cases,selected_rows=a.rows,selected_owner=a.row_start,owners=a.owners,physical_bankgroups=bg-a.bankgroup_base),indent=2)+'\n')

if __name__=='__main__':main()
