"""Emit an opt-in serial W12 DSpark layer with explicit norms and block attention.

No weights are loaded. Caller supplies actual matrix/constant image metadata.
All K/V slots are produced before any slot's attention. Every instruction has
an engine-drain barrier; there is no overlap pricing. Target verify ISA is
untouched. Context K/V ingest, final head and Markov epilogue are separate
stages: this emitter qualifies only the five repeated drafter layer programs.
"""
from __future__ import annotations

import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_isa_w12 as QI
import hdc_qwen_fullshape_program_w12 as FP
import qwen_rom_verify_program_w12 as V


def freeze_dyn(fields, lay, position, context):
    f = dict(fields)
    dyn = P.dyn_values(lay, token=0, pos=position)
    dyn[I.DYN_T] = context
    for base in ('wbase', 'xbase', 'obase', 'nout', 'tiles', 'k'):
        key = 'me_d_' + base
        selector = f.get(key, 0)
        if selector == I.DYN_TTILES:
            value = (context - 1) // (I.W_LANES * (lay.groups >> f['me_split'])) + 1
        else:
            value = dyn[selector]
        f['me_' + base] = f.get('me_' + base, 0) + value
        f[key] = 0
    f['su_nin'] = f.get('su_nin', 0) + dyn[f.get('su_d_nin', 0)]
    f['su_d_nin'] = 0
    for operand in 'abcd':
        key = operand + '_d'
        f[operand + '_base'] = f.get(operand + '_base', 0) + dyn[f.get(key, 0)]
        f[key] = 0
    # Conservative issue: no element chase and no overlap between operations.
    f.update(barrier=1, chase=0, chase_n=0, wait_me=0, wait_su=0)
    return f


def layer_program(lay, slots, start, post_scale_bases, *, enabled=False):
    if not enabled:
        raise ValueError('DSpark drafter ISA is default-off')
    if lay.tp != 4 or getattr(lay, 'norm_fold', True):
        raise ValueError('drafter requires TP4 and explicit norms')
    if slots not in (3, 7) or start < 0 or start + slots > FP.TMAX:
        raise ValueError('drafter position block exceeds KV window')
    if len(post_scale_bases) != 2:
        raise ValueError('o/down require two post-fold scale bases')
    vms, _ = V.vm_map_p(slots)
    programs = []
    for j, vm in enumerate(vms):
        with FP.program_geometry(vm):
            programs.append(P.build_program(lay, layers=[0], embed=False, head=False, scale_bases=True))
    if len({len(p) for p in programs}) != 1:
        raise ValueError('slot programs have different operation order')
    out, scale_index = [], 0
    for group in zip(*programs):
        collective = group[0].get('_coll')
        if collective:
            if any(f.get('_coll', (None,))[0] != collective[0] for f in group):
                raise ValueError('slot collectives disagree')
            kind = collective[0]
            if kind == P.COLL_ALLREDUCE:
                out.append(dict(unit=I.UNIT_END, barrier=1,
                                _coll=(kind, 0, slots * lay.H // I.W_LANES, 0)))
                for vm in vms:
                    out.append(dict(unit=I.UNIT_SU, barrier=1, su_nout=1, su_nin=lay.H,
                                    a_base=vm['T1'], a_si=1, c_src=I.SRC_ALT,
                                    c_base=post_scale_bases[scale_index], c_si=1, mc=I.MC_C,
                                    dst=I.DST_VM, d_base=vm['T1'], d_si=1))
                scale_index += 1
            elif kind == P.COLL_END:
                out.append(dict(unit=I.UNIT_END, barrier=1, _coll=collective))
            else:
                raise ValueError('unexpected drafter layer collective')
        else:
            for j, fields in enumerate(group):
                out.append(freeze_dyn(fields, lay, start + j, start + slots))
    if scale_index != 2:
        raise ValueError('missing o/down folds')
    return out


def encode_layer(lay, slots, start, post_scale_bases, *, enabled=False):
    program = layer_program(lay, slots, start, post_scale_bases, enabled=enabled)
    words, desc = [], []
    for instructions, (kind, base, count, row0) in P.segments(program):
        desc.append(V.encode_descriptor(kind, base, count, len(words), row0))
        words.extend(QI.encode_instruction(f) for f in instructions)
    if len(words) > 1024 or len(desc) > 64:
        raise ValueError('drafter layer exceeds companion program memory')
    return words, desc
