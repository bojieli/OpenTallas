#!/usr/bin/env python3
"""Export source-bound fusion candidates from saved HBM SU cases only.

Descriptors are software adapter input, not ISA words or an executable schedule.
The original operation sequence remains authoritative, including interleaving.
No arithmetic, golden, model inference, preparation, simulation or build runs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from hbm_accel_su_fused_compile_cases import (
    check_records, field_widths, input_records, load_cases, words_record,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'opentallas.hbm-su-fused-software-descriptors.v1'


def match(op, **expected):
    """Match every saved opcode field, including all otherwise-zero controls."""
    return all(value == expected.get(key, 0) for key, value in op.items())


def f32_bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def unique_before(ops, before, predicate):
    hits = [index for index in range(before) if predicate(ops[index])]
    return hits[0] if len(hits) == 1 else None


def initialized(case, address, count):
    return count > 0 and any(int(base) <= address and address+count <= int(base)+len(values)
                             for base, values in case['init'])


def vm_reads(op):
    return [(op[p+'base'], op[p+'base']+(op['nout']-1)*op[p+'so']+
             (op['nin']-1)*op[p+'si']+1)
            for p in ('a', 'b', 'c', 'd') if op[p+'src'] == 0]


def norm_groups(case, ops):
    fn = case['meta'].get('fn')
    if fn not in ('hc_pre_norm', 'final_norm', 'q_norm_kv_row'):
        return []
    groups = []
    for final_index, final in enumerate(ops):
        n, x, rs, y, gain = (final[k] for k in ('nin', 'abase', 'bbase', 'obase', 'cbase'))
        if n <= 0 or not match(final, nout=1, nin=n, abase=x, aso=n, asi=1,
                              bbase=rs, m1=1, csrc=1, cbase=gain, cso=n, csi=1,
                              e1=1, rnd=1, dst=1, obase=y, oso=n, osi=1):
            continue
        scalar_index = unique_before(ops, final_index, lambda op: op['obase'] == rs and
                                     op['m1'] == 5 and op['sfu'] == 2)
        if scalar_index is None:
            continue
        scalar = ops[scalar_index]
        ss, eps = scalar['abase'], scalar['imm2']
        if not match(scalar, nout=1, nin=1, abase=ss, m1=5, imm1=f32_bits(n),
                     ad=4, imm2=eps, sfu=2, dst=1, obase=rs):
            continue
        reduction_index = unique_before(ops, scalar_index, lambda op: op['rbase'] == ss and
                                        op['red'] == 1 and op['redsq'] == 1)
        if reduction_index is None:
            continue
        reduction = ops[reduction_index]
        seg = 8 if n % 64 == 0 else 1
        red = dict(nout=seg, nin=n // seg, aso=n // seg, asi=1,
                   red=1, redsq=1, redtree=int(seg > 1), redwhole=int(seg == 1), rbase=ss)
        indexes = [reduction_index, scalar_index, final_index]
        extra = {}
        if gain < 0 or gain+n > len(case['cr_lo']):
            continue
        if fn in ('hc_pre_norm', 'final_norm'):
            if seg != 8:
                continue
            h, pre, t = reduction['abase'] - 3 * n, reduction['bbase'] - 3, reduction['cbase']
            if not initialized(case, h, 4*n) or not initialized(case, pre, 4):
                continue
            extra = {'hc_VM_word_address': h, 'pre_VM_word_address': pre,
                     'mix_VM_word_address': t, 'hc_count': 4}
            red.update(abase=h + 3*n, bbase=pre + 3, m1=1, cbase=t, cso=n//seg, csi=1,
                       ad=2, rnd=1, dst=1, obase=x, oso=n//seg, osi=1)
            if not match(reduction, **red):
                continue
            second = unique_before(ops, reduction_index, lambda op: match(
                op, nout=1, nin=n, abase=h+2*n, aso=n, asi=1, bbase=pre+2, m1=1,
                cbase=t, cso=n, csi=1, ad=2, dst=1, obase=t, oso=n, osi=1))
            if second is None:
                continue
            first = unique_before(ops, second, lambda op: match(
                op, nout=1, nin=n, abase=h, aso=n, asi=1, bbase=pre, m1=1,
                cbase=h+n, cso=n, csi=1, dbase=pre+1, qm=1, ad=1,
                dst=1, obase=t, oso=n, osi=1))
            if first is None:
                continue
            indexes = [first, second, *indexes]
            kind = 'hc_norm'
        else:
            if not initialized(case, x, n):
                continue
            red.update(abase=x)
            if not match(reduction, **red):
                continue
            checked_q = any(label == 'qr' and address == y and len(want) == n
                            for label, address, want, _ in case['checks'])
            # The other norm must feed the saved in-place KV RoPE tail.
            kv_tail = any(op['cpair'] == 1 and op['abase'] == y+n-op['nin'] and
                          op['obase'] == op['abase'] and op['rnd'] == 1 for op in ops[final_index+1:])
            if not checked_q and not kv_tail:
                continue
            kind = 'q_norm' if checked_q else 'kv_norm'
        groups.append((kind, indexes, {'epsilon_u32': eps, 'gain_CR_word_address': gain,
                                     'input_VM_word_address': x, 'output_VM_word_address': y,
                                     'count': n, 'sum_square_VM_word_address': ss, **extra}, None))
    return groups


def hcpost_groups(case, ops):
    if case['meta'].get('fn') != 'hc_post':
        return []
    groups = []
    for end, final in enumerate(ops):
        hc, n, y, post, t = (final[k] for k in ('nout', 'nin', 'abase', 'bbase', 'obase'))
        if hc != 4 or n <= 0:
            continue
        expected = dict(nout=hc, nin=n, abase=y, asi=1, bbase=post, bso=1,
                        m1=1, cbase=t, cso=n, csi=1, ad=2, rnd=1,
                        dst=1, obase=t, oso=n, osi=1)
        side_effect = None
        if final['red'] or final['redsq']:
            expected.update(red=1, redsq=1, redtree=1, rbase=final['rbase'])
            side_effect = {'reason': 'hcpost engine lacks saved redsq side output; retain whole original group',
                           'original_op_index': end, 'reduction_contract': dict(final)}
        if not match(final, **expected):
            continue
        # There are two AD_C accumulations; locate them by exact linked addresses below.
        previous = [index for index in range(end) if ops[index]['obase'] == t and ops[index]['ad'] == 2]
        if len(previous) != 2:
            continue
        second, third = previous
        first = unique_before(ops, second, lambda op: op['obase'] == t and op['ad'] == 1)
        if first is None:
            continue
        h, comb = ops[first]['abase'], ops[first]['bbase']
        if not all(initialized(case, address, count) for address, count in
                   ((h, 4*n), (comb, 16), (y, n), (post, 4))):
            continue
        if not match(ops[first], nout=hc, nin=n, abase=h, asi=1, bbase=comb, bso=1,
                     m1=1, cbase=h+n, csi=1, dbase=comb+4, dso=1, qm=1, ad=1,
                     dst=1, obase=t, oso=n, osi=1):
            continue
        if not all(match(ops[index], nout=hc, nin=n, abase=h+j*n, asi=1,
                         bbase=comb+4*j, bso=1, m1=1, cbase=t, cso=n, csi=1,
                         ad=2, dst=1, obase=t, oso=n, osi=1)
                   for index, j in ((second, 2), (third, 3))):
            continue
        groups.append(('hc_post', [first, second, third, end],
                       {'residual_VM_word_address': h, 'Y_VM_word_address': y,
                        'comb_VM_word_address': comb, 'post_VM_word_address': post,
                        'output_VM_word_address': t, 'count': n, 'hc': hc}, side_effect))
    return groups


def swiglu_groups(case, ops):
    if case['meta'].get('fn') != 'swiglu':
        return []
    groups = []
    for index, op in enumerate(ops):
        n, a, c, b, out, route, limit = (op[k] for k in
                                      ('nin', 'abase', 'cbase', 'bbase', 'obase', 'e2', 'imm3'))
        if n <= 0 or route not in (0, 1) or not match(
                op, nout=1, nin=n, abase=a, aso=n, asi=1, amin=1, imm3=limit,
                sfu=5, cbase=c, cso=n, csi=1, cclip=1, e1=1, e2=route,
                bbase=b, rnd=1, dst=1, obase=out, oso=n, osi=1):
            continue
        if not initialized(case, a, n) or not initialized(case, c, n) or (
                route and not initialized(case, b, 1)):
            continue
        groups.append(('swiglu', [index], {'gate_VM_word_address': a, 'up_VM_word_address': c,
                       'route_weight_VM_word_address': b if route else None,
                       'clip_limit_u32': limit, 'output_VM_word_address': out, 'count': n}, None))
    return groups


def indexq_groups(case, ops):
    if case['meta'].get('fn') != 'index_q' or len(ops) != 2:
        return []
    rope, weight = ops
    ih, rd, a, out, table = (rope[k] for k in ('nout', 'nin', 'abase', 'obase', 'bbase'))
    ihd = rope['aso']
    n, w, wo = (weight[k] for k in ('nin', 'abase', 'obase'))
    if not (ih > 0 and rd > 0 and rd % 2 == 0 and ihd >= rd and n > 0):
        return []
    if not match(rope, nout=ih, nin=rd, abase=a, aso=ihd, asi=1, cpair=1,
                 bsrc=1, bbase=table, bsi=1, bhalf=1, dsrc=2, dbase=table,
                 dsi=1, m1=1, qm=3, ad=1, rnd=1, dst=1, obase=out, oso=ihd, osi=1):
        return []
    if not match(weight, nout=1, nin=n, abase=w, aso=n, asi=1, m1=3,
                 imm1=weight['imm1'], rnd=1, dst=1, obase=wo, oso=n, osi=1):
        return []
    q = a-ihd+rd
    if not initialized(case, q, ih*ihd) or not initialized(case, w, n) or (
            table < 0 or table+rd//2 > min(len(case['cr_lo']), len(case['cr_hi']))):
        return []
    groups = [('index_q', [0, 1], {'heads': ih, 'head_width': ihd, 'rotated_tail_words': rd,
              'original_Q_VM_word_address': q, 'rotated_tail_VM_word_address': out,
              'table_CR_word_address': table, 'weight_VM_word_address': w,
              'scaled_weight_VM_word_address': wo, 'weights': n,
              'weight_scale_u32': weight['imm1'], 'quantization': 'not lowered in saved ops',
              'per_head_quant_input': {'untouched_head': {'source': 'original Q', 'base': q,
                                        'count': ihd-rd, 'head_stride': ihd},
                                      'rotated_tail': {'source': 'saved RoPE output', 'base': out,
                                                       'count': rd, 'head_stride': ihd}},
              'weight_rounding': 'saved rnd=1 BF16; do not quantize weights'}, None)]
    return groups


def compile_case(case, index, pickle_sha, widths):
    ops = [{key: int(value) for key, value in op.items()} for op in case['ops']]
    malformed = any(set(op) != set(widths) or any(value < 0 or value >= 1 << widths[key]
                    for key, value in op.items()) for op in ops)
    groups = [] if malformed else (norm_groups(case, ops) + hcpost_groups(case, ops) +
                                   swiglu_groups(case, ops) + indexq_groups(case, ops))
    selected = set()
    candidates = []
    for kind, indexes, operands, side_effect in sorted(groups, key=lambda group: min(group[1])):
        if selected.intersection(indexes):
            continue
        # Fusion cannot cross a separate writer of any consumed/intermediate VM word.
        group_writes = []
        group_reads = []
        for i in indexes:
            op = ops[i]
            group_reads.extend(vm_reads(op))
            if op['dst']:
                group_writes.append((op['obase'], op['obase'] +
                                     (op['nout']-1)*op['oso'] + (op['nin']-1)*op['osi'] + 1))
            if op['red']:
                group_writes.append((op['rbase'], op['rbase']+(op['nout']-1)*op['rso']+1))
        interfering = False
        for i in range(min(indexes), max(indexes)+1):
            if i in indexes:
                continue
            op = ops[i]
            writes = []
            if op['dst']:
                writes.append((op['obase'], op['obase']+(op['nout']-1)*op['oso']+(op['nin']-1)*op['osi']+1))
            if op['red']:
                writes.append((op['rbase'], op['rbase']+(op['nout']-1)*op['rso']+1))
            if (any(lo < other_hi and other_lo < hi for lo, hi in group_writes+group_reads
                    for other_lo, other_hi in writes)
                    or any(lo < other_hi and other_lo < hi for lo, hi in group_writes
                           for other_lo, other_hi in vm_reads(op))):
                interfering = True
                break
        if interfering:
            continue
        active = side_effect is None
        if active:
            selected.update(indexes)
        candidates.append({'kind': kind, 'selected': active, 'original_op_indexes': indexes,
                           'original_ops': [ops[i] for i in indexes], 'operands': operands,
                           'retained_side_effect': side_effect})
    return {'original_case_index': index, 'name': case['name'], 'meta': case['meta'],
            'original_ops': ops, 'inputs': input_records(case),
            'CR_lo': words_record(case['cr_lo']), 'CR_hi': words_record(case['cr_hi']),
            'checks': check_records(case, pickle_sha), 'candidates': candidates,
            'retained_op_indexes': [i for i in range(len(ops)) if i not in selected],
            'fallback_reason': 'invalid saved opcode field contract' if malformed else
                'unsupported operation/address contract retained unchanged' if not candidates else None,
            'original_order_authoritative': True,
            'downstream_quant_boundary': {'saved_also_bitexact_window_row': case['meta']['also_bitexact_window_row'],
                                         'native_quant_not_in_saved_ops': True}
                if 'also_bitexact_window_row' in case['meta'] else None}


def compile_saved(path: Path, root: Path = ROOT, *, case_index: int | None = None):
    blob, sha = load_cases(path)
    if case_index is not None and not 0 <= case_index < len(blob['cases']):
        raise ValueError('case_index is outside the actual saved cases')
    widths = field_widths(root)
    cases = [compile_case(case, i, sha, widths) for i, case in enumerate(blob['cases'])
             if case_index is None or i == case_index]
    return {'schema': SCHEMA, 'descriptor_encoding': 'software v1, NOT native ISA words',
            'saved_cases': {'path': str(path), 'sha256': sha,
                            'snapshots_sha256': blob.get('snapshots_sha256')},
            'opcode_field_widths': widths, 'cases': cases,
            'summary': {'cases': len(cases), 'selected_by_kind': dict(Counter(
                candidate['kind'] for case in cases for candidate in case['candidates'] if candidate['selected'])),
                'retained_ops': sum(len(case['retained_op_indexes']) for case in cases)},
            'source_sha256': {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in (
                'tools/hbm_accel_su_fused_compile.py', 'tools/hbm_accel_su_fused_compile_cases.py',
                'tools/dshbm_baseline_measure.py', 'tools/dshbm_1m_local.py',
                'tools/hdc_isa_v41.py', 'tools/rtl_hdc_v41x_vec_campaign.py')},
            'arithmetic_executed': False, 'RTL_measured': False, 'adopted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--case-index', type=int, help='Export only this original saved case index')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = compile_saved(args.cases, case_index=args.case_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['summary']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
