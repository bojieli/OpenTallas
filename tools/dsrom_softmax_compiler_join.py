#!/usr/bin/env python3
"""Source-bound layout lowering for the experimental softmax transport.

These pure index maps are ready for an opt-in compiler/adapter integration;
the production stream-unit instruction lowering remains unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H, LPH, TD = 16, 16, 64


def vm_to_softmax(columns):
    """VM head-major -> vectors containing16 consecutive values per head."""
    if columns not in (128, 512, 640):
        raise ValueError('unqualified row shape')
    return [[head * columns + vector * LPH + lane
             for head in range(H) for lane in range(LPH)]
            for vector in range(columns // LPH)]


def exp_to_probability_words(tokens):
    """Indices into exp stream: TD BF16 values, row-major across H heads.

    Data still needs exactly one rne16 conversion at the adapter boundary.
    This maps the actual PWORDS=1,TD=64 engine port, not a generic vector link.
    """
    if tokens not in (128, 640):
        raise ValueError('unqualified token shape')
    rows_per_word = TD // H
    return [[(row // LPH) * (H * LPH) + head * LPH + row % LPH
             for row in range(first, first + rows_per_word) for head in range(H)]
            for first in range(0, tokens, rows_per_word)]


def check(tokens):
    source = list(range(H * tokens))  # identity tags, independent VM scoreboard
    stream = [source[i] for vector in vm_to_softmax(tokens) for i in vector]
    actual = [stream[i] for word in exp_to_probability_words(tokens) for i in word]
    expected = [head * tokens + row for row in range(tokens) for head in range(H)]
    assert actual == expected
    assert sorted(i for v in vm_to_softmax(tokens) for i in v) == source
    # Raw exp order into P.V is a realistic missing-transpose negative.
    assert stream != expected
    return dict(tokens=tokens, score_and_exp_vectors=tokens//LPH,
                probability_words=tokens//(TD//H), probability_port_bits=TD*16,
                all_indices_unique=True, missing_transpose_negative_detected=True)


def build():
    sources = ['tools/dsrom_1m_su.py', 'rtl/hdc/v41x/ot_dsrom_su_softmax.sv',
               'rtl/hdc/v41x/ot_hdc_v41x_attn.sv',
               'rtl/w17_runtime/hdc/v41x/ot_hdc_v41x_att_adapt.sv']
    text = (ROOT/sources[-1]).read_text()
    assert 'xbuf[(hb + ph) * TROWS + pb * TD + pw * R + pj]' in text
    assert 'xbuf[((l2_c + lq) / kx) * TROWS + (l2_c + lq) % kx] <= rne16' in text
    pv_map = vm_to_softmax(512)
    assert sorted(i for row in pv_map for i in row) == list(range(H*512))
    return dict(schema='opentallas.dsrom_softmax_compiler_join.v1',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        campaigns=[check(t) for t in (128,640)],
        production_lowering_changed=False, adopted=False,
        instructions=['gather VM S0[h*T+t] into score[v][h*16+lane]',
            'dispatch scores with atomically held nv/lt/scale/sink/cos/sin',
            'scatter exp vectors into VM E[h*T+t] or apply exp_to_probability_words at direct adapter',
            'apply existing adapter rne16 exactly once before P.V; do not reinterpret FP32 bits as BF16',
            'wait actual attention P.V output, gather PV[h*512+d]',
            'wait actual den_v, then replay PV vectors to normalize',
            'scatter BF16 output to head-major O; shift BF16 code left16 when storing BF16-as-FP32 VM words'],
        result_VM_representation='BF16 code shifted left16, not integer zero extension in lowbits',
        remaining=['bind production instruction encoding and row tags',
            'attention score/PV tile output gather and credits',
            'RTL transpose/beat assembler and protected reservation control',
            'exact numerical producer→consumer test on actual row',
            'native clock/CDC and full timing composition'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
    args=parser.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text)
    print(text,end='')
