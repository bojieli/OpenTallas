#!/usr/bin/env python3
"""hbm-forks (2026-10-09): HGI-1 v0.9 record encoder + a reference model of the command-processor sequencer (C2,
docs/HBM_GENERIC_INTERFACE.md 3.1-3.5), and the CF-PROG smoke vectors for rtl/hbm_accel/generic/tb/tb_hgi_seq.sv.

Field positions come from tools/hbm_generic_iface.py (UOP_FIELDS, MDESC_FIELDS, UNITS, OPS, DYN).  The reference
model is the sequencer's architectural contract: in-order records, predicate, the `wait` drain mask, one LOOP level
(body replayed), DYN banks per slot, effective base = base + L*lstride + DYN[dyn_sel]*dyn_mul (40 bits), n = DYN[n_sel]
when n_sel != 0, CTL.END completion with the posted result token range-checked against cp_vocab.

Writes rtl/hbm_accel/generic/tb/hgi_seq_{image,expect,cfg}.mem and hgi_seq_vectors.json.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_generic_iface as G  # noqa: E402

UOP = {n: (l, w) for n, l, w in G.UOP_FIELDS}
MD = {n: (l, w) for n, l, w in G.MDESC_FIELDS}
UNIT = {n: i for i, n in enumerate(G.UNITS)}
OPC = {u: {o: i for i, o in enumerate(ops)} for u, ops in G.OPS.items()}
DYN = {n: i for i, n in enumerate(G.DYN)}
M40 = (1 << 40) - 1


def put(d, fields, v=0):
    for k, x in d.items():
        l, w = fields[k]
        assert 0 <= x < (1 << w), (k, x)
        v |= x << l
    return v


def header(unit, op, wait=0, pred=0, opnd=0, tmpl=0, slot=0, param=0, imm_a=0, imm_b=0):
    return put(dict(unit=UNIT[unit], op=OPC[unit][op], wait=wait, pred=pred, opnd=opnd, tmpl=tmpl, slot=slot,
                    param=param, imm_a=imm_a, imm_b=imm_b), UOP)


def mdesc(**kw):
    return put(kw, MD)


def record(hdr, sut=None, descs=()):
    words = [hdr]                                   # 128-bit words
    opnd = (hdr >> UOP['opnd'][0]) & 0xF
    tmpl = (hdr >> UOP['tmpl'][0]) & 1
    assert len(descs) == bin(opnd).count('1') and (sut is not None) == bool(tmpl)
    if tmpl:
        words += [sut & ((1 << 128) - 1), sut >> 128]
    for d in descs:
        words += [d & ((1 << 128) - 1), d >> 128]
    return words


def field(v, fields, k):
    l, w = fields[k]
    return (v >> l) & ((1 << w) - 1)


class Ref:
    """the sequencer contract on a list of records; returns the dispatch trace and the completion"""
    def __init__(self, recs, token, pos, rank, vocab, res):
        self.recs, self.token, self.pos, self.rank, self.vocab, self.res = recs, token, pos, rank, vocab, res

    def dyn(self, sel, slot, L):
        v = dict(ZERO=0, POS=self.pos, POS1=self.pos + 1, TOKEN=self.token, L=L, RANK=self.rank, SLOT=slot,
                 POS_SLOT=self.pos + slot)
        return v[G.DYN[sel]]

    def run(self):
        out, i, L, loop = [], 0, 0, None
        while True:
            words = self.recs[i]
            h = words[0]
            unit, op = G.UNITS[field(h, UOP, 'unit')], field(h, UOP, 'op')
            opn = G.OPS[unit][op]
            pred, slot = field(h, UOP, 'pred'), field(h, UOP, 'slot')
            last = loop is not None and L == loop[1] - 1
            ok = [True, self.pos == 0, self.pos != 0, last][pred]
            nxt = i + 1
            if unit == 'CTL':
                if opn == 'LOOP':
                    loop, L = (i + 1, field(h, UOP, 'param')), 0
                elif opn == 'ENDLOOP':
                    if L + 1 < loop[1]:
                        L += 1; nxt = loop[0]
                    else:
                        loop, L = None, 0
                elif opn == 'END' and ok:
                    st = 3 if (self.res >> 18) or self.res >= self.vocab else 0
                    return out, (self.res & 0x3FFFF, st)
                i = nxt
                continue
            if ok:
                tmpl = field(h, UOP, 'tmpl')
                k = 1 + 2 * tmpl
                eff = []
                for j in range(4):
                    if (field(h, UOP, 'opnd') >> j) & 1:
                        d = words[k] | (words[k + 1] << 128); k += 2
                        base = field(d, MD, 'base') + L * field(d, MD, 'lstride') + \
                            self.dyn(field(d, MD, 'dyn_sel'), slot, L) * field(d, MD, 'dyn_mul')
                        n = field(d, MD, 'n') if field(d, MD, 'n_sel') == 0 else self.dyn(field(d, MD, 'n_sel'), slot, L)
                        d2 = d & ~(M40 << MD['base'][0]) & ~(((1 << 20) - 1) << MD['n'][0])
                        d2 |= (base & M40) << MD['base'][0] | (n & 0xFFFFF) << MD['n'][0]
                        eff.append(d2)
                    else:
                        eff.append(0)
                sut = (words[1] | (words[2] << 128)) if tmpl else 0
                out.append((G.UNITS.index(unit), h, sut, eff, L))
            i = nxt


def program(rng):
    """a 10+-record smoke: every unit class the dispatcher drives, a LOOP of 3 with L strides, every DYN selector,
    n_sel, all four predicates, waits on SM / SU / COLL, a FENCE, then END"""
    R = []
    R.append(record(header('DMA', 'LOAD', opnd=0b1001, param=0),
                    descs=[mdesc(space=0, fmt=1, base=0x1000, n=128, dyn_sel=DYN['TOKEN'], dyn_mul=4128),
                           mdesc(space=1, fmt=0, base=0x40, n=128)]))
    R.append(record(header('CTL', 'LOOP', param=3)))
    R.append(record(header('FUSED', 'ROW_NORM', wait=1 << UNIT['DMA'], opnd=0b1011, param=0, imm_a=0x358637BD),
                    descs=[mdesc(space=1, base=0x40, n=4096, lstride=0x100), mdesc(space=0, base=0x20000, n=4096, lstride=0x4000),
                           mdesc(space=1, base=0x2000, n=4096, lstride=0x10)]))
    R.append(record(header('SM', 'MATVEC', opnd=0b1011, param=3),
                    descs=[mdesc(space=2, n=4096), mdesc(space=0, fmt=4, base=0x100_0000, n=4096, m=1536, lstride=0x60_0000),
                           mdesc(space=2, n=1536)]))
    R.append(record(header('SU', 'VOP', wait=1 << UNIT['SM'], opnd=0b1001, tmpl=1, slot=2),
                    sut=rng.getrandbits(256),
                    descs=[mdesc(space=1, base=0x3000, n=128, dyn_sel=DYN['POS_SLOT'], dyn_mul=2),
                           mdesc(space=0, base=0x800_0000, n=0, n_sel=DYN['POS1'], dyn_sel=DYN['POS'], dyn_mul=256, lstride=0x10_0000)]))
    R.append(record(header('ATT', 'QK', wait=1 << UNIT['SU'], opnd=0b1011, param=0x14),
                    descs=[mdesc(space=1, base=0x3000, n=128), mdesc(space=0, base=0x900_0000, n=0, n_sel=DYN['POS1'],
                           lstride=0x20_0000), mdesc(space=1, base=0x5000, n=0, n_sel=DYN['POS1'])]))
    R.append(record(header('COLL', 'ALL_REDUCE_SUM', wait=(1 << UNIT['ATT']) | (1 << UNIT['SU']), opnd=0b1001),
                    descs=[mdesc(space=1, base=0x6000, n=4096, dyn_sel=DYN['RANK'], dyn_mul=1024), mdesc(space=1, base=0x7000, n=4096)]))
    R.append(record(header('DMA', 'STORE', pred=3, opnd=0b1001, wait=1 << UNIT['COLL']),     # last iteration only
                    descs=[mdesc(space=1, base=0x7000, n=64), mdesc(space=0, base=0xA00_0000, n=64, dyn_sel=DYN['POS'], dyn_mul=64,
                           lstride=0x1_0000)]))
    R.append(record(header('CTL', 'ENDLOOP')))
    R.append(record(header('SFU', 'GLU', pred=1, opnd=0b1111),                                # pos == 0 only
                    descs=[mdesc(space=1, base=1), mdesc(space=1, base=2), mdesc(space=1, base=3), mdesc(space=1, base=4)]))
    R.append(record(header('ARGMAX', 'LOCAL', pred=2, opnd=0b1001, wait=0xFFF),               # pos != 0 only, full drain
                    descs=[mdesc(space=2, n=37984), mdesc(space=1, base=0x8000, n=2)]))
    R.append(record(header('CTL', 'FENCE')))
    R.append(record(header('CTL', 'END', wait=1 << UNIT['ARGMAX'], opnd=0b0001),
                    descs=[mdesc(space=1, fmt=5, base=0x8000, n=1)]))
    return R


def main():
    rng = random.Random(20261009)
    recs = program(rng)
    words = [w for r in recs for w in r]
    cases = []
    for (token, pos, rank, vocab, res) in ((151935, 4095, 2, 151936, 777), (0, 0, 0, 129280, 129279),
                                           (5, 8191, 3, 151936, 151936)):
        tr, cpl = Ref(recs, token, pos, rank, vocab, res).run()
        cases.append(dict(token=token, pos=pos, rank=rank, vocab=vocab, res=res, trace=tr, cpl=cpl))
    D = ROOT / 'rtl/hbm_accel/generic/tb'
    (D / 'hgi_seq_image.mem').write_text('\n'.join(f'{w:032X}' for w in words) + '\n')
    cfg, exp = [], []
    for c in cases:
        cfg.append(f"{c['token']:08X} {c['pos']:08X} {c['rank']:08X} {c['vocab']:08X} {c['res']:08X} "
                   f"{len(c['trace']):08X} {c['cpl'][0]:08X} {c['cpl'][1]:08X}")
        for (u, h, sut, eff, L) in c['trace']:
            exp.append(f"{u:032X}")
            exp.append(f"{h:032X}")
            exp.append(f"{sut:064X}")
            exp += [f"{e:064X}" for e in eff]
    (D / 'hgi_seq_cfg.mem').write_text('\n'.join(cfg) + '\n')
    # expect stream: per dispatch 1 + 1 + 1 + 4 lines (unit, header, sut, A, B, C, O) as 256-bit hex lines
    (D / 'hgi_seq_expect.mem').write_text('\n'.join(x.rjust(64, '0') for x in exp) + '\n')
    (D / 'hgi_seq_vectors.json').write_text(json.dumps(dict(
        schema='opentallas.hgi_seq_vectors.v1', spec='results/arch/hbm_generic_iface_20261009/spec.json',
        records=len(recs), words128=len(words),
        cases=[dict(token=c['token'], pos=c['pos'], rank=c['rank'], vocab=c['vocab'], res=c['res'],
                    dispatches=[(G.UNITS[u], L) for u, _, _, _, L in c['trace']], cpl=c['cpl']) for c in cases]),
        indent=1) + '\n')
    print(len(recs), 'records,', len(words), 'words;', [(len(c['trace']), c['cpl']) for c in cases])


if __name__ == '__main__':
    main()
