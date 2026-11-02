#!/usr/bin/env python3
"""Canonical component gold for actual tile0's first four HEAD K-splits.

Uses the genuine recovered tile0 codes and model norm, with controlled causal
RES2 X32 and repository rsqrt(1024). No selected clock, programme or upstream
transport qualification is inferred. Output is unscaled PART1, not logits.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_golden as G
import numpy as np


def build(codes_path, norm_path, consumer):
    c=json.loads(consumer.read_text()); norm=json.loads(norm_path.read_text())
    if (c['groups'],c['tile_groups'],c['tile_id'],c['code_words']) != (3072,4,0,1600):
        raise ValueError('requires selected genuine tile0 TG4 / HEAD1600 source')
    words=[int(x,16) for x in codes_path.read_text().split()]
    if len(words)!=1600 or any(w>>512 for w in words):
        raise ValueError('actual four-group INT8 excerpt shape changed')
    gain_bits={}
    for s in norm['slices']:
        for r in s['gain_payloads']:
            payload=int(r['payload_hex'],16)
            for lane,index in enumerate(r['global_elements']):
                gain_bits[index]=(payload>>(64*lane))&0xffffffff
    if sorted(gain_bits)!=list(range(4096)):
        raise ValueError('complete genuine model norm required')
    gains=G.from_bits(np.array([gain_bits[i] for i in range(32)],dtype=np.uint32))
    rstd=G.rsqrt(G.F(1024))
    h=G.mul(G.mul(G.F(32),rstd),gains)
    # Canonical shipped layout: word = round*kc*IL + kk*IL + slot,
    # byte = (q*split+c)*W + lane. Tile0 has q0/c0..3, kc8/IL8/W16.
    weights=np.zeros((25*128,32),dtype=np.float32);rows=[]
    for round_ in range(25):
        for slot in range(8):
            for lane in range(16):
                out=round_*128+slot*16+lane
                rows.append(round_*768+slot*16+lane)
                for group in range(4):
                    for kk in range(8):
                        value=(words[round_*64+kk*8+slot]>>(8*(group*16+lane)))&255
                        weights[out,group*8+kk]=value-256 if value&128 else value
    partial=G.matvec(weights,h,4)
    # A genuine input corruption must affect the numeric oracle, independently
    # of any simulator observation or fitted expected values.
    mutant=weights[:1].copy();mutant[0,0]+=1 if mutant[0,0]<127 else -1
    mutated=G.matvec(mutant,h,4)
    if int(G.bits(mutated[0]))==int(G.bits(partial[0])):
        raise ValueError('chosen real first-code mutation did not affect oracle')
    meta=dict(schema='native_head_tile0_partial_gold/1',source_only=True,rtl_executed=False,
        scope='unscaled actual TG4 PART1 partial; no global tree, BF16 scale, AMAX or selected physical claim',
        rows=3200,columns=32,k_split=4,chunk_length=8,
        row_mapping='round*768 + slot*16 + lane; round0..24,slot0..7,lane0..15',
        source_layout='hdc_qwen_int8_image_w12.matrix_code/engine_word_arrays: round*64+kk*8+slot; bytegroup*16+lane',
        controlled_input=dict(raw_residual_fp32='42000000',mean_fp32='44800000',rstd_fp32=f'{int(G.bits(rstd)):08x}',
            H='mul(mul(FP32(32),canonical_rsqrt(FP32(1024))),genuine_model_norm); matvec rounds H to BF16',
            consumer_input='STREAM BF16-RNE(H), expanded to FP32 with low16 zero; do not truncate raw upstream H',
            upstream_status='controlled component input; producer/clock/calendar transport not qualified'),
        oracle='hdc_golden.matvec: separate RNE mul/add sequential eight terms from+0, pairwise four-chunk tree',
        mutant=dict(field='first actual INT8 weight',gold_hex=f'{int(G.bits(partial[0])):08x}',mutant_hex=f'{int(G.bits(mutated[0])):08x}'),
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (codes_path,norm_path,consumer,Path(G.__file__))})
    return meta,rows,h,partial


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('codes','norm','consumer','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m,rows,h,gold=build(a.codes,a.norm,a.consumer);a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'row_indices.hex').write_text(''.join(f'{r:06x}\n'for r in rows))
    (a.out/'H32_fp32.hex').write_text(''.join(f'{int(x):08x}\n'for x in G.bits(h)))
    (a.out/'H32_me_fp32.hex').write_text(''.join(f'{int(x):08x}\n'for x in G.bits(G.to_bf16(h))))
    (a.out/'H32_bf16.hex').write_text(''.join(f'{int(x)>>16:04x}\n'for x in G.bits(G.to_bf16(h))))
    (a.out/'raw_partial_expected.hex').write_text(''.join(f'{int(x):08x}\n'for x in G.bits(gold)))
    (a.out/'oracle.json').write_text(json.dumps(m,indent=2)+'\n')
    print(json.dumps(dict(rows=m['rows'],rstd=m['controlled_input']['rstd_fp32'],first_partial=m['mutant']['gold_hex'],mutant=m['mutant']['mutant_hex'],source_only=True)))


if __name__=='__main__':main()
