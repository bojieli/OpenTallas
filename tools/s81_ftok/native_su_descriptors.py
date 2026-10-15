#!/usr/bin/env python3
"""Encode compiler-assigned SU descriptors without numerical fixture operands.

This is a partial native allocation contract, not an executable native program.
RoPE and gain producers, real field/collective writes, and every transport edge
must still be bound by the whole-program compiler.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def emit(layer, model_config):
    config = json.loads(model_config.read_text())
    eps = config['norm_eps']
    eps_bits = struct.unpack('<I', struct.pack('<f', eps))[0]
    source = dict(path=str(model_config), sha256=hashlib.sha256(model_config.read_bytes()).hexdigest())
    jobs, tensors = {}, {}
    for tail, kind, gain, descriptor, ibase, nrows, obase, outrows, count in (
            ('q_quant', 0, 1, 12288, 4096, 80, 4176, 25, 0),
            ('kv_rope_qdq', 1, 2, 12304, 4224, 32, 4256, 25, 0),
            ('q_rope', 10, 0, 12320, 4304, 512, 4304, 512, 16)):
        name = f'{layer}.attn.{tail}'
        words = [obase, ibase, count, eps_bits if kind != 10 else 0] + [0]*12
        jobs[name] = dict(engine='su', endpoint='dsfd_sp_su_h', arg=(kind << 20) | (gain << 18) | descriptor,
                          descriptor_row=descriptor, descriptor_words=words,
                          descriptor_hex=f'{sum(w << (32*i) for i,w in enumerate(words)):0128x}',
                          descriptor_parameter_rows=list(range(descriptor, descriptor+(1 if kind==0 else 5))),
                          native_qualified=False, schedule_bound=False)
        tensors[name+'.input'] = dict(base_row=ibase, nrows=nrows, source='native_job',
                                      producer=None, consumers=[name], producer_bound=False,
                                      format='16 FP32 values per512-bit row')
        tensors[name+'.output'] = dict(base_row=obase, nrows=outrows, source='native_job', producer=name,
                                       consumers=[], producer_bound=False,
                                       format=('five tiles: four FP8-code rows then one exponent row each' if kind==0 else
                                               'eight FP8-code rows, one exponent row, sixteen packed BF16 rows' if kind==1 else
                                               'FP32 heads in place; only tail rows28..31 of each32-row head are written'))
        if kind in (1,10):
            tensors[name+'.rope'] = dict(base_row=descriptor+1,nrows=4,source='resident_constant',
                                         producer=None,consumers=[name],producer_bound=False,
                                         format='cos32 then sin32 FP32 values; native boot path required')
    return dict(schema='opentallas.s81.native_su_descriptors.v1',layer=layer,
                native_qualified=False,complete_program=False,constant_source=source,eps_bits=eps_bits,
                jobs=jobs,tensors=tensors,
                required_gain_owners={f'{layer}.constant.q_norm_gain':dict(nrows=80,gain_kind='GQ',gain_set=1,producer_bound=False),
                                      f'{layer}.constant.kv_norm_gain':dict(nrows=32,gain_kind='GK',gain_set=2,producer_bound=False)},
                missing=['field/allgather actual output tag and capture permutation bindings',
                         'resident constants native boot producer and VM writes',
                         'field consumer mapping for interleaved FP8 codes/exponents',
                         'fixed issue/ingress/enqueue/service/response/commit calendars',
                         'actual endpoint elaboration and complete operation coverage'])


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--layer',default='L0')
    p.add_argument('--model-config',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(emit(a.layer,a.model_config),indent=1)+'\n')
