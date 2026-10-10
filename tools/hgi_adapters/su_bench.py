#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): bench vectors for ot_hgi_su_record (SU.VOP -> the stream unit's vec op word).

Writes, into --out (default rtl/hbm_accel/generic/adapters/tb/su):
  su_rec.mem   one dispatch a line: {n_A 21, I, R, O, D, C, B, A (7 x 256), SUT 256, header 128}  (2,197 bits)
  su_ref.mem   the reference op word a line: {kind 2, word 670}; kind 0 run, 1 empty op (retire, no issue), 2 refuse
  su_case.mem  {kind, first dispatch, dispatches, first vm_in, vm_in words, first vm_out, vm_out words} (7 x 32 b)
               case kind 0 = DATA (hbm-sim conformance vector run on the real ot_hdc_v41x_vec: VM out == expect),
               1 = FIELDS (Qwen3-8B token program SU records, unique, stub unit), 2 = NEGATIVE (one record, reset after)
  su_vmi.mem / su_vme.mem   {addr 32, value 32}
  su_bench.json  the manifest (case ids, counts, sources)
The reference word is computed here from the spec text (6.6, 6.9; hgi_sim machine.u_su_vop) independently of the RTL.
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

sys.path.insert(0, str(C.ROOT / 'tools'))
import rtl_hdc_v41x_vec_campaign as V  # noqa: E402

SUTL = [('a_src', 0, 2), ('a_ind', 2, 2), ('b_src', 4, 2), ('b_half', 6, 1), ('c_src', 7, 2), ('c_pair', 9, 1),
        ('d_src', 10, 2), ('a_rnd', 12, 1), ('a_relu', 13, 1), ('a_min', 14, 1), ('c_clip', 15, 1), ('m1', 16, 3),
        ('m2', 19, 2), ('qm', 21, 3), ('ad', 24, 3), ('sfu', 27, 3), ('e1', 30, 3), ('e2', 33, 2), ('rnd', 35, 1),
        ('dst', 36, 2), ('red', 38, 2), ('red_sq', 40, 1), ('red_whole', 41, 1), ('red_rnd', 42, 1), ('su_vec', 43, 2),
        ('red_tree', 45, 1), ('imm1', 46, 32), ('imm2', 78, 32), ('imm3', 110, 32)]
WORD_BITS = 670


def sut_fields(s):
    return {n: (s >> lo) & ((1 << w) - 1) for n, lo, w in SUTL}


def ref_word(d):
    """(kind, word) for one SU dispatch d (Ref trace entry)."""
    h, s = d['hdr'], sut_fields(d['sut'])
    op = {k: C.fld(h, k, C.UOP) for k in ('unit', 'op', 'opnd', 'tmpl')}
    pres = {nm: bool(op['opnd'] >> j & 1) for j, nm in enumerate(C.OPND)}
    D = {nm: d['eff'][j] for j, nm in enumerate(C.OPND)}
    sp = {nm: C.fld(D[nm], 'space') for nm in C.OPND}
    use_b = s['m1'] in (1, 4, 6) or s['ad'] == 3 or s['e2'] == 1
    use_c = (s['m2'] == 1 or s['qm'] != 0 or s['ad'] in (1, 2) or s['e1'] in (1, 2)) and not s['c_pair']
    use_d = s['qm'] != 0 or s['ad'] == 5
    no, ni = C.fld(D['A'], 'm'), d['n'][0]
    refuse = (op['unit'] != 2 or op['op'] != 0 or not op['tmpl'] or d['sut'] >> 142 or s['su_vec'] or not pres['A']
              or any(pres[k] and sp[k] != 1 for k in C.OPND)
              or any(s[k] for k in ('a_src', 'b_src', 'c_src', 'd_src'))
              or (use_b and not pres['B']) or (use_c and not pres['C']) or (use_d and not pres['D'])
              or s['a_ind'] == 3 or (s['a_ind'] and not pres['I'])
              or s['dst'] in (2, 3) or (s['dst'] == 1 and not pres['O']) or (s['red'] and not pres['R'])
              or no >= 1 << 16 or ni >= 1 << 16)
    if refuse:
        return 2, 0
    if no == 0 or ni == 0:
        return 1, 0
    M24 = (1 << 24) - 1

    def si(x):
        return 0 if C.fld(x, 'ibcast') else (C.fld(x, 'istride') or 1)

    f = V.op_defaults()
    f.update(nout=no, nin=ni, aind=s['a_ind'], bhalf=s['b_half'], cpair=s['c_pair'], arnd=s['a_rnd'],
             arelu=s['a_relu'], amin=s['a_min'], cclip=s['c_clip'], m1=s['m1'], m2=s['m2'], qm=s['qm'], ad=s['ad'],
             sfu=s['sfu'], e1=s['e1'], e2=s['e2'], rnd=s['rnd'], dst=s['dst'], red=s['red'], redsq=s['red_sq'],
             redwhole=s['red_whole'], redtree=s['red_tree'], redrnd=s['red_rnd'], imm1=s['imm1'], imm2=s['imm2'],
             imm3=s['imm3'], aibase=C.fld(D['I'], 'base') & M24, rbase=C.fld(D['R'], 'base') & M24,
             rso=(C.fld(D['R'], 'stride') or 1) & M24)
    for k in 'ABCDO':
        x = D[k]
        f[k.lower() + 'base'] = C.fld(x, 'base') & M24
        f[k.lower() + 'so'] = C.fld(x, 'stride') & M24
        f[k.lower() + 'si'] = si(x) & M24
    w = V.encode(f)
    return 0, w & ((1 << WORD_BITS) - 1)


def sfu_as_su(d):
    """SFU.GLU dispatch -> the equivalent SU.VOP dispatch (ot_hgi_sfu_record header), or None when refused"""
    h = d['hdr']
    opnd = C.fld(h, 'opnd', C.UOP)
    O = d['eff'][4]
    if (C.fld(h, 'unit', C.UOP) != 3 or C.fld(h, 'op', C.UOP) != 0 or C.fld(h, 'tmpl', C.UOP) or (opnd & 0b10111) != 0b10111
            or C.fld(O, 'fmt') not in (0, 1)):
        return None
    sut = sut_word(a_min=1, c_clip=1, sfu=5, e1=1, e2=1, rnd=int(C.fld(O, 'fmt') == 1), dst=1,
                   imm3=C.fld(h, 'imm_a', C.UOP))
    eff = [d['eff'][0], d['eff'][2], d['eff'][1], 0, O, 0, 0]
    return dict(hdr=C.SV.header(2, 0, opnd=0b0010111, tmpl=1), sut=sut, eff=eff, n=[d['n'][0]] + [0] * 6)


def ref_any(d, unit):
    if unit == 'su':
        return ref_word(d)
    e = sfu_as_su(d)
    return (2, 0) if e is None else ref_word(e)


def mdesc(space=1, fmt=0, base=0, n=0, m=1, stride=0, istride=0, ibcast=0):
    return C.SV.mdesc(space=space, fmt=fmt, base=base, n=n, m=m, stride=stride, istride=istride, ibcast=ibcast)


def sut_word(**kw):
    w = 0
    pos = {n: (lo, wd) for n, lo, wd in SUTL}
    for k, v in kw.items():
        lo, wd = pos[k]
        w |= (v & ((1 << wd) - 1)) << lo
    return w


def synth(unit=2, op=0, tmpl=1, sut=0, descs=None, n_a=None, rsv=0):
    descs = descs or {}
    opnd = sum(1 << j for j, nm in enumerate(C.OPND) if nm in descs)
    h = C.SV.header(unit, op, opnd=opnd, tmpl=tmpl)
    eff = [descs.get(nm, 0) for nm in C.OPND]
    n = [C.fld(e, 'n') for e in eff]
    if n_a is not None:
        n[0] = n_a
    return dict(hdr=h, sut=sut | (rsv << 200), eff=eff, n=n)


def negatives():
    A = mdesc(base=0, n=64, m=2, stride=64)
    O = mdesc(base=4096, n=64, m=2, stride=64)
    B = mdesc(base=1024, n=64, m=2, stride=64)
    ok = dict(dst=1)
    neg = [('unit_not_su', synth(unit=3, sut=sut_word(**ok), descs=dict(A=A, O=O))),
           ('op_not_vop', synth(op=1, sut=sut_word(**ok), descs=dict(A=A, O=O))),
           ('no_template', synth(tmpl=0, descs=dict(A=A, O=O))),
           ('sut_reserved_bit', synth(sut=sut_word(**ok), descs=dict(A=A, O=O), rsv=1)),
           ('su_vec_set', synth(sut=sut_word(su_vec=1, **ok), descs=dict(A=A, O=O))),
           ('a_in_hbm', synth(sut=sut_word(**ok), descs=dict(A=mdesc(space=0, base=0, n=64, m=2, stride=256), O=O))),
           ('o_in_stream', synth(sut=sut_word(**ok), descs=dict(A=A, O=mdesc(space=2, n=64, m=2)))),
           ('b_src_rom', synth(sut=sut_word(b_src=1, m1=1, **ok), descs=dict(A=A, B=B, O=O))),
           ('m1_ab_without_b', synth(sut=sut_word(m1=1, **ok), descs=dict(A=A, O=O))),
           ('qm_without_d', synth(sut=sut_word(qm=1, **ok), descs=dict(A=A, C=B, O=O))),
           ('dst_kv', synth(sut=sut_word(dst=2), descs=dict(A=A, O=O))),
           ('dst_vm_without_o', synth(sut=sut_word(**ok), descs=dict(A=A))),
           ('red_without_r', synth(sut=sut_word(red=1), descs=dict(A=A))),
           ('gather_without_i', synth(sut=sut_word(a_ind=1, **ok), descs=dict(A=A, O=O))),
           ('a_ind_3', synth(sut=sut_word(a_ind=3, **ok), descs=dict(A=A, O=O, I=mdesc(fmt=5, base=2000, n=64)))),
           ('nin_2p16', synth(sut=sut_word(**ok), descs=dict(A=A, O=O), n_a=1 << 16)),
           ('no_a', synth(sut=sut_word(**ok), descs=dict(O=O)))]
    nop = [('nout_0', synth(sut=sut_word(**ok), descs=dict(A=mdesc(base=0, n=64, m=0), O=O))),
           ('nin_0', synth(sut=sut_word(**ok), descs=dict(A=A, O=O), n_a=0))]
    return neg, nop


def pack_rec(d):
    w = d['hdr'] | d['sut'] << 128
    for j in range(7):
        w |= (d['eff'][j] & ((1 << 256) - 1)) << (384 + 256 * j)
    w |= (d['n'][0] & ((1 << 21) - 1)) << (384 + 1792)
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(C.ROOT / 'rtl/hbm_accel/generic/adapters/tb/su'))
    ap.add_argument('--unit', default='su', choices=['su', 'sfu'])
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    recs, refs, cases, vmi, vme, man = [], [], [], [], [], []

    def add_case(kind, ident, ds, vm_in=None, vm_out=None):
        cases.append((kind, len(recs), len(ds), len(vmi), len(vm_in or {}), len(vme), len(vm_out or {})))
        for d in ds:
            recs.append(pack_rec(d))
            k, w = ref_any(d, a.unit)
            refs.append(k << WORD_BITS | w)
        vmi.extend(sorted((vm_in or {}).items()))
        vme.extend(sorted((vm_out or {}).items()))
        man.append(dict(kind=['data', 'fields', 'negative'][kind], id=ident, dispatches=len(ds),
                        ref_kinds=[ref_any(d, a.unit)[0] for d in ds]))

    if a.unit == 'sfu':
        for v, tr, cpl, vm in C.conformance(lambda v: {r['unit'] for r in v['records']} <= {'SFU', 'CTL'}):
            ds = [d for d in tr if C.unit_of(d) == 3]
            if ds and v['expect']['status'] == 0:
                add_case(0, v['id'], ds, vm, C.vm_out_of(v['expect']['dies'][0]))
        tr, _ = C.qwen_dispatch()
        seen, uq = set(), []
        for d in tr:
            key = (d['hdr'], tuple(d['eff']), d['n'][0])
            if C.unit_of(d) == 3 and key not in seen:
                seen.add(key)
                uq.append(d)
        add_case(1, 'qwen3_8b_token_sfu_unique', uq)
        A = mdesc(base=0, n=64, m=1)
        def g(**kw):
            descs = kw.pop('descs', dict(A=A, B=mdesc(base=100, n=64), C=mdesc(base=200, n=64), O=mdesc(base=300, n=64)))
            dd = synth(unit=3, tmpl=kw.pop('tmpl', 0), descs=descs)
            dd['hdr'] = C.SV.header(kw.get('unit', 3), kw.get('op', 0), opnd=C.fld(dd['hdr'], 'opnd', C.UOP),
                                    tmpl=C.fld(dd['hdr'], 'tmpl', C.UOP), imm_a=0x7F7FFFFF)
            return dd
        add_case(1, 'glu_fp32_bf16_out', [g(), g(descs=dict(A=A, B=mdesc(base=100, n=64), C=mdesc(base=200, n=64, ibcast=1),
                                                            O=mdesc(base=300, fmt=1, n=64)))])
        for name, d in [('unit_not_sfu', g(unit=2)), ('op_1', g(op=1)), ('template', g(tmpl=1)),
                        ('no_c', g(descs=dict(A=A, B=mdesc(base=100, n=64), O=mdesc(base=300, n=64)))),
                        ('o_fp8', g(descs=dict(A=A, B=mdesc(base=100, n=64), C=mdesc(base=200, n=64), O=mdesc(base=300, fmt=2, n=64)))),
                        ('b_in_hbm', g(descs=dict(A=A, B=mdesc(space=0, base=100, n=64), C=mdesc(base=200, n=64), O=mdesc(base=300, n=64))))]:
            add_case(2, name, [d])
        write(out, recs, refs, cases, vmi, vme, man)
        return
    # DATA: conformance vectors whose records are SU.VOP + CTL only
    for v, tr, cpl, vm in C.conformance(lambda v: {r['unit'] for r in v['records']} <= {'SU', 'CTL'}):
        su = [d for d in tr if C.unit_of(d) == 2]
        if not su or v['expect']['status'] != 0:
            continue
        add_case(0, v['id'], su, vm, C.vm_out_of(v['expect']['dies'][0]))
    # FIELDS: the Qwen3-8B token program's SU records (unique dispatches)
    tr, _ = C.qwen_dispatch()
    seen, uq = set(), []
    for d in tr:
        if C.unit_of(d) != 2:
            continue
        key = (d['hdr'], d['sut'], tuple(d['eff']), d['n'][0])
        if key not in seen:
            seen.add(key)
            uq.append(d)
    add_case(1, 'qwen3_8b_token_su_unique', uq)
    # random legal records over the template space (fields only)
    rng = random.Random(20261009)
    rl = []
    for _ in range(64):
        s = dict(a_ind=rng.choice([0, 0, 1, 2]), b_half=rng.randint(0, 1), c_pair=rng.randint(0, 1),
                 a_rnd=rng.randint(0, 1), a_relu=rng.randint(0, 1), a_min=rng.randint(0, 1), c_clip=rng.randint(0, 1),
                 m1=rng.randint(0, 6), m2=rng.randint(0, 2), qm=rng.randint(0, 4), ad=rng.randint(0, 5),
                 sfu=rng.randint(0, 7), e1=rng.randint(0, 4), e2=rng.randint(0, 2), rnd=rng.randint(0, 1),
                 dst=1, red=rng.randint(0, 3), red_sq=rng.randint(0, 1), red_whole=rng.randint(0, 1),
                 red_rnd=rng.randint(0, 1), red_tree=rng.randint(0, 1), imm1=rng.getrandbits(32),
                 imm2=rng.getrandbits(32), imm3=rng.getrandbits(32))

        def rd():
            return mdesc(base=rng.randrange(1 << 18), n=rng.randrange(1, 4096), m=rng.randrange(1, 64),
                         stride=rng.getrandbits(32), istride=rng.choice([0, 0, 1, 2, rng.getrandbits(16)]),
                         ibcast=rng.choice([0, 0, 0, 1]))
        rl.append(synth(sut=sut_word(**s), descs=dict(A=rd(), B=rd(), C=rd(), D=rd(), O=rd(), R=rd(),
                                                      I=mdesc(fmt=5, base=rng.randrange(1 << 18), n=8))))
    add_case(1, 'random_legal_templates_64', rl)
    neg, nop = negatives()
    add_case(1, 'empty_ops', [d for _, d in nop])
    for name, d in neg:
        add_case(2, name, [d])
    write(out, recs, refs, cases, vmi, vme, man)


def write(out, recs, refs, cases, vmi, vme, man):
    (out / 'su_rec.mem').write_text(''.join(C.hexw(r, 2197) + '\n' for r in recs))
    (out / 'su_ref.mem').write_text(''.join(C.hexw(r, 672) + '\n' for r in refs))
    (out / 'su_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    (out / 'su_vmi.mem').write_text(''.join(f'{a:08X}{x:08X}\n' for a, x in vmi) or '0000000000000000\n')
    (out / 'su_vme.mem').write_text(''.join(f'{a:08X}{x:08X}\n' for a, x in vme) or '0000000000000000\n')
    (out / 'su_sizes.svh').write_text('// GENERATED by tools/hgi_adapters/su_bench.py\n' + ''.join(
        f'localparam integer {k} = {v};\n' for k, v in dict(NREC=len(recs), NCASE=len(cases), NVMI=max(1, len(vmi)),
                                                          NVME=max(1, len(vme))).items()))
    (out / 'su_bench.json').write_text(json.dumps(dict(schema='opentallas.hgi_adapters.su_bench.v1', cases=man,
                                                       dispatches=len(recs), vm_in_words=len(vmi),
                                                       vm_out_words=len(vme)), indent=1) + '\n')
    print(f"{len(cases)} cases, {len(recs)} dispatches, data cases "
          f"{sum(1 for c in man if c['kind'] == 'data')}: {[c['id'] for c in man if c['kind'] == 'data']}")


if __name__ == '__main__':
    main()
