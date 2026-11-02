#!/usr/bin/env python3
"""Emit relocatable native HEAD gain payloads and apply-H instruction objects.

No address, PROG slot or calendar is allocated. The source object uses existing
s8 X/RX regions and the native (X*RSTD)*gain arithmetic order; the gain CROM
base remains a linker relocation. Production installation requires leases,
user relocation, a HEAD loader window and real scalar/operand dates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
import dv_lower as D
import dv_lower_vec as V


def gains(path, meta):
    lines = Path(path).read_text().splitlines()
    if len(lines) != 4096 or any(len(w) != 16 for w in lines):
        raise ValueError('exactly4096 low-FP32/high-zero source words required')
    words = [int(w, 16) for w in lines]
    if any(w >> 32 for w in words):
        raise ValueError('gain high half must be zero')
    source = meta['norm_source']
    if source['dtype'] == 'BF16':
        if any(w & 0xffff for w in words):
            raise ValueError('BF16 source has nonzero discarded bits')
        raw = struct.pack('<4096H', *(w >> 16 for w in words))
    elif source['dtype'] == 'F32':
        raw = struct.pack('<4096I', *words)
    else:
        raise ValueError('unsupported original final-norm dtype')
    if hashlib.sha256(raw).hexdigest() != source['source_tensor_sha256']:
        raise ValueError('gain words differ from recovered checkpoint tensor')
    return words


def build(words, own):
    blocks = own['residual']['blocks_per_slice']
    if own.get('slice_rtl') != 's8' or len(blocks) != 12 or sorted(b for row in blocks for b in row) != list(range(32)):
        raise ValueError('actual s8 residual ownership must cover32 blocks once')
    if len(words) != 4096 or any(type(w) is not int or not 0 <= w < 1 << 32 for w in words):
        raise ValueError('4096 exact FP32 words required')
    vm = D.vm_map(own)
    c_offset = sum(width for field, width in D.SU_FIELDS[:next(i for i, (field, _) in enumerate(D.SU_FIELDS) if field == 'c')])
    slices = []
    for sid, row in enumerate(blocks):
        if not row or (len(row) > 1 and any(b-a != row[1]-row[0] for a, b in zip(row, row[1:]))):
            raise ValueError('residual block ownership must have one native stride')
        stride = row[1]-row[0] if len(row) > 1 else 0
        local = [words[128*b+j] for b in row for j in range(128)]
        payloads = []
        for start in range(0, len(local), 16):
            payload = sum(word << (64*j) for j, word in enumerate(local[start:start+16]))
            payloads.append(dict(relative_crom_row=start//16, payload_hex=f'{payload:0256x}',
                                 global_elements=[128*row[(start+j)//128]+(start+j)%128 for j in range(16)]))
        # Same native MA_AB then MC path as the existing QK gain instruction.
        # C=0 is an unresolved relocation, never an allocated HEAD address.
        word = D.su_word(nout=len(row), nin=128, a=vm['X']['base'], aso=128, asi=1,
                         b=vm['RX']['base'], ma=V.MA_AB, csrc=1, c=0, cso=128,
                         csi=1, mc=1, dst=V.DST_VM, d=D.W_X | (128*row[0]),
                         dso=128*stride, dsi=1)
        slices.append(dict(slice=sid, blocks=row, words=len(local), gain_payloads=payloads,
                           apply_su_template_hex=f'{word:0115x}',
                           relocations=[dict(symbol='HEAD_GAIN_CROM_BASE', field='c', bit=c_offset, width=24, unit='FP32_element')],
                           prog_slot=None, user_relocation='required_after_HEAD_allocation',
                           arithmetic='native MA_AB(X,RSTD), then MC(result,CROM_gain); W_X BF16 output'))
    return dict(schema='opentallas.qwen.native-head-norm-object.v1', status='UNLINKED_SOURCE_OBJECT',
                stage=37, native_instruction_bits=457, scalar_producer='existing final residual2 PSUM -> ROOT fused RSTD',
                extra_ssq_commands=0, gain_elements=4096, gain_payloads=sum(len(s['gain_payloads']) for s in slices),
                slices=slices, blocked_on=['HEAD_GAIN CROM allocation and reload/live-range lease peruser',
                'HEAD PROG allocation and stage37 table-loader/BOOT installation',
                'final residual2/ROOT RSTD publication and lifetime through apply-H',
                'native CALR SU issue and STREAM/HEAD consume dates',
                'actual native arithmetic and programme replay'],
                executable=False, boot_transport='NOT_INSTALLED', calendar='NOT_EMITTED')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--gain-words', type=Path, required=True)
    ap.add_argument('--head-data', type=Path, required=True)
    ap.add_argument('--plan', default=D.PLAN)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    meta = json.loads(a.head_data.read_text())
    own = D.ownership(a.plan, 's8')
    result = build(gains(a.gain_words, meta), own)
    result['sources'] = dict(ownership=own['sources'], recovered_gain_tensor=meta['norm_source'],
                             checkpoint_revision=meta['checkpoint_revision'],
                             gain_words_sha256=hashlib.sha256(a.gain_words.read_bytes()).hexdigest())
    a.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','gain_elements','gain_payloads','executable')}))

if __name__ == '__main__':
    main()
