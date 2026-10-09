#!/usr/bin/env python3
"""hbm-forks (2026-10-09): HGI-1 v1.0 (NORMATIVE, owner-approved) record encoder, a reference model of the
command-processor sequencer (docs/HBM_GENERIC_INTERFACE.md 2.2, 3.1-3.5, 4.2, 6.1-6.8), and the bench vectors of
rtl/hbm_accel/generic/tb/tb_hgi_seq.sv (CF-PROG, CF-LOOP2, CF-IDXD, CF-CP absent-unit / range, DS DYN codes).

Every field position comes from tools/hbm_generic_iface.py's v1.0 tables (D_UOP_FIELDS, D_MDESC_FIELDS, D_UNITS, D_OPS,
D_OPND, D_DYN, NSEL_FROM_VM), so a spec change shows up here without edits.

The reference model is the sequencer's architectural contract:
  * records in program order; header + [SUT] + one MDESC per opnd bit in A, B, C, D, O, R, I order;
  * predicate ALWAYS / POS0 / NOT_POS0 / LAST_ITER (the innermost active loop);
  * CTL.LOOP param[15:0] count, [16] level (0 -> L, 1 -> L1), two levels nested in either order, bodies replayed;
  * effective base = base + L*lstride + L1*l1stride + X*dyn_mul (strides signed 32-bit), X = DYN[dyn_sel] or, for an
    indexed descriptor, U32(VM[I_eff + L]); n = n (n_sel 0) | DYN[n_sel] (1..62) | U32(VM[I_eff + I.stride + L]) (63);
  * DYN: 0 ZERO 1 POS 2 POS1 3 TOKEN 4 L 5 RANK 6 SLOT 7 POS_SLOT 8 L1 15 POS_SLOT1, 16..40 = the DS full-shape
    selectors (hdc_isa_v41.FULL_DYN_KEYS order) at the slot's position; 9..14 (window / chunk, reserved) and 41..63
    fault (status 3);
  * faults, status 3 (bad command or range): a unit code >= 11 (SIMT absent on r25, 12..15 reserved), an op code
    outside the unit's list, CTL.TOKX / AMAX / ACCEPT (reserved until the Qwen MTP decision), a reserved DYN code,
    an indexed / N_FROM_VM descriptor without an I descriptor (or an I that is itself indexed / N_FROM_VM, or not in
    VM), an I-table read outside VM, an effective HBM base outside [0, 2^40) or VM base outside [0, 2^18), an n from
    VM >= 2^21, a LOOP of count 0, a third nested LOOP or a level already active, an ENDLOOP with no loop, a loop body
    larger than the prefetch ring, END without an A descriptor in VM, END token >= 2^18 or >= cp_vocab; a doorbell
    with token >= cp_vocab or pos >= cp_ctx_max completes at once with status 3.  A unit fault -> status 1.
  * END: token = U32(VM[A_eff]) after END's wait mask.
The dispatch payload: the header, the SUT, the 7 EFFECTIVE descriptors (base field = effective base, n field = the
effective n's low 20 bits; every other field as encoded) + full-width sidebands: 7 x 21-bit effective n, POS1,
POS_SLOT1 of the record's slot, L, L1.

The Qwen3-8B token program (embed, 36 layers in one LOOP, head) is the hbm-sim compiler's (tools/hgi_sim/
qwen_compiler.program, at P = 8,192, pos 8,191) re-encoded in v1.0, and every non-indexed effective base / n is checked
against the simulator's addressing (Machine.eff) before a vector is written.
  python3 tools/hgi_seq_vectors.py         (writes rtl/hbm_accel/generic/tb/hgi_seq_*.mem + hgi_seq_vectors.json)
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_generic_iface as G  # noqa: E402

UOP = {n: (l, w) for n, l, w in G.D_UOP_FIELDS}
MD = {n: (l, w) for n, l, w in G.D_MDESC_FIELDS}
UNITS = G.D_UNITS
UNIT = {n: i for i, n in enumerate(UNITS)}
OPS = G.D_OPS
OPC = {u: {o: i for i, o in enumerate(ops)} for u, ops in OPS.items()}
OPND = G.D_OPND                       # A B C D O R I
DYN = {n: i for i, n in enumerate(G.D_DYN)}
NFV = G.NSEL_FROM_VM                  # 63
SPACE = {'HBM': 0, 'VM': 1, 'STREAM': 2, 'NONE': 3}
FMT = {'FP32': 0, 'BF16': 1, 'FP8E4M3': 2, 'FP4E2M1': 3, 'INT8': 4, 'U32': 5, 'UE8M0': 6}
M40, M20, M21 = (1 << 40) - 1, (1 << 20) - 1, (1 << 21) - 1
RW = 512                              # prefetch ring words (16 B) = ot_hgi_seq RW
NUNIT_OK = 11                         # units 0..10 exist on r25
# DS full-shape DYN parameters (tools/v41_fullshape_isa.py: TP, WINDOW, SCAN_CAP, TOPK, HD) = ot_hgi_seq parameters
DS_TP, DS_WIN, DS_SCAN, DS_TOPK, DS_HD = 4, 128, 16384, 512, 512


def put(d, fields, v=0):
    for k, x in d.items():
        l, w = fields[k]
        assert 0 <= x < (1 << w), (k, x)
        v |= x << l
    return v


def field(v, fields, k):
    l, w = fields[k]
    return (v >> l) & ((1 << w) - 1)


def s32(x):
    return x - (1 << 32) if x & (1 << 31) else x


def header(unit, op, wait=0, pred=0, opnd=0, tmpl=0, slot=0, param=0, imm_a=0, imm_b=0):
    return put(dict(unit=UNIT[unit] if isinstance(unit, str) else unit,
                    op=OPC[unit][op] if isinstance(op, str) else op, wait=wait, pred=pred, opnd=opnd, tmpl=tmpl,
                    slot=slot, param=param, imm_a=imm_a & 0xFFFFFFFF, imm_b=imm_b & 0xFFFFFFFF), UOP)


def mdesc(**kw):
    kw = dict(kw)
    for k in ('stride', 'lstride', 'l1stride'):
        if k in kw:
            kw[k] &= 0xFFFFFFFF
    return put(kw, MD)


def record(hdr, sut=None, descs=None):
    """descs: dict slot-name -> 256-bit MDESC"""
    descs = descs or {}
    opnd = sum(1 << i for i, k in enumerate(OPND) if k in descs)
    hdr &= ~(((1 << 7) - 1) << UOP['opnd'][0])
    hdr |= opnd << UOP['opnd'][0]
    hdr &= ~(1 << UOP['tmpl'][0])
    hdr |= int(sut is not None) << UOP['tmpl'][0]
    words = [hdr]
    if sut is not None:
        words += [sut & ((1 << 128) - 1), sut >> 128]
    for k in OPND:
        if k in descs:
            words += [descs[k] & ((1 << 128) - 1), descs[k] >> 128]
    return words


def ds_full(ps, rank):
    """the 25 DS full-shape selectors (hdc_isa_v41.FULL_DYN_KEYS order) at position ps (= pos + slot)"""
    p1 = ps + 1
    n2 = p1 >> 1
    cd = lambda a, b: -(-a // b)  # noqa: E731
    ns1, ns2 = min(p1, DS_TOPK), min(n2, DS_TOPK)
    win = min(p1, DS_WIN)
    sc1, sc2, scr = cd(p1, DS_TP), cd(n2, DS_TP), cd(min(p1, DS_SCAN), DS_TP)
    newblk = (ps - rank * sc1) // 8 if rank * sc1 <= ps < (rank + 1) * sc1 else cd(sc1, 8)
    return [win, p1, n2, ns1, ns2, win, win + ns1, win + ns2, sc1, sc2, scr, min(sc1, DS_TOPK), min(sc2, DS_TOPK),
            min(scr, DS_TOPK), cd(sc1, 16), cd(sc1, 8), cd(sc2, 16), cd(scr, 16), cd(win, 32), cd(win + ns1, 32),
            cd(win + ns2, 32), win - 1, win * DS_HD, (win - 1) * DS_HD, newblk]


class Fault(Exception):
    pass


class Ref:
    """The sequencer contract.  words: the program image as 128-bit words; vm: dict addr -> u32 (the VM the
    sequencer reads: I tables, the END token); on_dispatch(k, unit, op) -> list of (addr, value) VM writes that
    unit makes (applied at dispatch: a program with correct waits reads them)."""

    def __init__(self, words, entry, token, pos, rank, vocab, ctxmax, vm, on_dispatch=None):
        self.w, self.entry = words, entry
        self.token, self.pos, self.rank, self.vocab, self.ctxmax = token, pos, rank, vocab, ctxmax
        self.vm = dict(vm)
        self.on_dispatch = on_dispatch or (lambda k, u, o: [])

    def vmr(self, a):
        if not 0 <= a < (1 << 18):
            raise Fault('VM read out of range')
        return self.vm.get(a, 0) & 0xFFFFFFFF

    def dyn(self, code, slot, L, L1):
        p = self.pos
        v = {0: 0, 1: p, 2: p + 1, 3: self.token, 4: L, 5: self.rank, 6: slot, 7: p + slot, 8: L1, 15: p + slot + 1}
        if code in v:
            return v[code]
        if 16 <= code <= 40:
            return ds_full(p + slot, self.rank)[code - 16]
        raise Fault(f'reserved DYN code {code}')

    def eff(self, d, slot, L, L1, ieff, idesc):
        base = field(d, MD, 'base') + L * s32(field(d, MD, 'lstride')) + L1 * s32(field(d, MD, 'l1stride'))
        if field(d, MD, 'indexed'):
            if ieff is None:
                raise Fault('indexed without I')
            X = self.vmr(ieff + L)
        else:
            X = self.dyn(field(d, MD, 'dyn_sel'), slot, L, L1)
        base += X * field(d, MD, 'dyn_mul')
        sp = field(d, MD, 'space')
        if sp == 0 and not 0 <= base <= M40:
            raise Fault('HBM base out of range')
        if sp == 1 and not 0 <= base < (1 << 18):
            raise Fault('VM base out of range')
        ns = field(d, MD, 'n_sel')
        if ns == 0:
            n = field(d, MD, 'n')
        elif ns == NFV:
            if ieff is None:
                raise Fault('N_FROM_VM without I')
            n = self.vmr(ieff + s32(field(idesc, MD, 'stride')) + L)
            if n > M21:
                raise Fault('n from VM out of range')
        else:
            n = self.dyn(ns, slot, L, L1) & M21
        e = d & ~(M40 << MD['base'][0]) & ~(M20 << MD['n'][0])
        e |= (base & M40) << MD['base'][0] | (n & M20) << MD['n'][0]
        return e, n

    def run(self):
        if self.token >= self.vocab or self.pos >= self.ctxmax:
            return [], (0, 3)
        out, i, stack, Lc = [], self.entry, [], [0, 0]
        self.toks = []
        try:
            while True:
                h = self.w[i]
                unit, op = field(h, UOP, 'unit'), field(h, UOP, 'op')
                opnd, tmpl, slot = field(h, UOP, 'opnd'), field(h, UOP, 'tmpl'), field(h, UOP, 'slot')
                param, pred = field(h, UOP, 'param'), field(h, UOP, 'pred')
                rlen = 1 + 2 * tmpl + 2 * bin(opnd).count('1')
                if unit >= NUNIT_OK or op >= len(OPS[UNITS[unit]]):
                    raise Fault('absent unit / op')
                if stack and i + rlen - stack[0][2] > RW - 2:
                    raise Fault('loop body larger than the ring')
                last = bool(stack) and Lc[stack[-1][0]] == stack[-1][1] - 1
                if not [True, self.pos == 0, self.pos != 0, last][pred]:
                    i += rlen
                    continue
                k = i + 1 + 2 * tmpl
                descs = {}
                for j, nm in enumerate(OPND):
                    if opnd >> j & 1:
                        descs[nm] = self.w[k] | (self.w[k + 1] << 128)
                        k += 2
                L, L1 = Lc
                ieff = idesc = None
                if 'I' in descs:
                    idesc = descs['I']
                    if field(idesc, MD, 'indexed') or field(idesc, MD, 'n_sel') == NFV or field(idesc, MD, 'space') != 1:
                        raise Fault('bad I')
                    e, _ = self.eff(idesc, slot, L, L1, None, None)
                    ieff = field(e, MD, 'base')
                if unit == 0:
                    name = OPS['CTL'][op]
                    if name == 'LOOP':
                        cnt, lvl = param & 0xFFFF, (param >> 16) & 1
                        if cnt == 0 or len(stack) == 2 or any(s[0] == lvl for s in stack):
                            raise Fault('bad LOOP')
                        Lc[lvl] = 0
                        stack.append((lvl, cnt, i + rlen))
                    elif name == 'ENDLOOP':
                        if not stack:
                            raise Fault('ENDLOOP without LOOP')
                        lvl, cnt, body = stack[-1]
                        if Lc[lvl] + 1 < cnt:
                            Lc[lvl] += 1
                            i = body
                            continue
                        stack.pop()
                        Lc[lvl] = 0
                    elif name == 'END':
                        if 'A' not in descs or field(descs['A'], MD, 'space') != 1:
                            raise Fault('END without a VM A')
                        e, _ = self.eff(descs['A'], slot, L, L1, ieff, idesc)
                        tok = self.vmr(field(e, MD, 'base'))
                        st = 3 if (tok >> 18) or tok >= self.vocab else 0
                        return out, (tok & 0x3FFFF, st)
                    elif name == 'TOKX':           # Q-MTP-1: k committed tokens (1..16) from VM[A_eff ..] onto the completion
                        if 'A' not in descs or field(descs['A'], MD, 'space') != 1:
                            raise Fault('TOKX without a VM A')
                        e, k = self.eff(descs['A'], slot, L, L1, ieff, idesc)
                        b0 = field(e, MD, 'base')
                        if not 1 <= k <= 16 or b0 + k > (1 << 18):
                            raise Fault('TOKX count out of range')
                        toks = [self.vmr(b0 + q) for q in range(k)]
                        if any((t >> 18) or t >= self.vocab for t in toks):
                            raise Fault('TOKX token out of range')
                        self.toks = toks
                    elif name in ('AMAX', 'ACCEPT'):
                        raise Fault('reserved CTL op')
                    i += rlen
                    continue
                effs, ns = [0] * 7, [0] * 7
                for j, nm in enumerate(OPND):
                    if nm in descs:
                        effs[j], ns[j] = self.eff(descs[nm], slot, L, L1, ieff, idesc)
                sut = (self.w[i + 1] | (self.w[i + 2] << 128)) if tmpl else 0
                out.append(dict(unit=unit, hdr=h, sut=sut, eff=effs, n=ns, L=L, L1=L1, pos1=self.pos + 1,
                                pslot1=self.pos + slot + 1, rec=i))
                for a, v in self.on_dispatch(len(out) - 1, UNITS[unit], OPS[UNITS[unit]][op]):
                    self.vm[a] = v
                i += rlen
        except Fault as f:
            self.fault = str(f)
            self.toks = []
            return out, (0, 3)


# ---------------------------------------------------------------------------------------------------------------------
# programs
# ---------------------------------------------------------------------------------------------------------------------
def qwen_program():
    """the hbm-sim compiler's Qwen3-8B token program (TP4, P = 8,192), encoded by the simulator itself (HGI-1 current
    design, tools/hgi_sim/records.py); returns (words, recs, g, md)"""
    from hgi_sim import qwen_compiler as QC
    from hgi_sim import records as SR
    cfg = json.loads((ROOT / G.MODELS['qwen3_8b']['cfg']).read_text())
    md = QC.qwen_params(cfg)
    g = QC.Geometry(cfg, 8192)
    recs = QC.program(g, md, cfg['num_hidden_layers'], parts=('embed', 'layers', 'head'))
    b = SR.encode_program(recs)
    words = [int.from_bytes(b[q:q + 16], 'little') for q in range(0, len(b), 16)]
    return words, recs, g, md


def sim_check(words, entry, trace, recs, pos, token, rank):
    """every effective base / n the reference dispatches equals the hbm-sim Machine.eff of the same record"""
    from hgi_sim import machine as M
    from hgi_sim import records as SR
    die = M.Die(rank, None)
    mach = M.Machine([die])
    idx, wi = {}, entry
    for r in recs:
        idx[wi] = r
        wi += SR.rec_bytes(r) // 16
    n = 0
    for d in trace:
        r = idx[d['rec']]
        die.dyn[:9] = [0, pos, pos + 1, token, d['L'], rank, r.slot, pos + r.slot, d['L1']]
        for j, nm in enumerate(OPND):
            if nm in r.desc:
                base, nn, *_ = mach.eff(r.desc[nm], die, d['L'])
                if (field(d['eff'][j], MD, 'base'), d['n'][j]) != (base & M40, nn):
                    raise AssertionError(f"record {r.tag} {nm}: seq {field(d['eff'][j], MD, 'base')}/{d['n'][j]} vs "
                                         f"sim {base}/{nn}")
                n += 1
    return n


def synth_program(rng, stale=False):
    """CF-LOOP2 + CF-IDXD + DS DYN + every unit class; stale=True drops the IDX wait of the indexed readers (the
    CF-IDXD stale-table negative: must FAIL)"""
    W = []
    wIDX = 0 if stale else (1 << UNIT['IDX'])
    R = lambda *a, **k: W.extend(record(*a, **k))  # noqa: E731
    R(header('DMA', 'LOAD', param=0), descs=dict(
        A=mdesc(space=0, fmt=1, base=0x1000, n=4096, dyn_sel=DYN['TOKEN'], dyn_mul=8192),
        O=mdesc(space=1, base=0x40, n=4096)))
    # CF-LOOP2: L outer (3) around L1 inner (2); l1stride, lstride, LAST_ITER on the inner loop, ibcast
    R(header('CTL', 'LOOP', param=3))
    R(header('CTL', 'LOOP', param=(1 << 16) | 2))
    R(header('SU', 'VOP', wait=1 << UNIT['DMA'], slot=1), sut=rng.getrandbits(142), descs=dict(
        A=mdesc(space=1, base=0x400, n=128, lstride=0x400, l1stride=-128),
        B=mdesc(space=1, ibcast=1, base=0x9000, n=128, l1stride=1),
        D=mdesc(space=0, base=0x9100, n=64, dyn_sel=DYN['POS_SLOT'], dyn_mul=64),
        O=mdesc(space=1, base=0xA000, n=128, lstride=0x200, l1stride=0x80),
        R=mdesc(space=1, base=0xB000, n=1, lstride=2, l1stride=1)))
    R(header('FUSED', 'ROW_NORM', pred=3, param=(0 << 6) | 32, imm_a=0x358637BD), descs=dict(
        A=mdesc(space=1, base=0xA000, n=4096, lstride=0x200), B=mdesc(space=0, base=0x20000, n=4096, lstride=0x4000),
        O=mdesc(space=1, fmt=1, base=0xC000, n=4096, dyn_sel=DYN['L1'], dyn_mul=4096)))
    R(header('CTL', 'ENDLOOP'))
    R(header('ATT', 'QK', wait=1 << UNIT['FUSED'], param=(1 << 8) | (1 << 4) | 8), descs=dict(
        A=mdesc(space=1, base=0xC000, n=128, m=8, stride=128),
        B=mdesc(space=0, fmt=2, base=0x900_0000, n=0, m=128, n_sel=DYN['POS1'], lstride=0x20_0000),
        C=mdesc(space=0, fmt=2, base=0xA00_0000, n=0, m=512, n_sel=DS_N['NS1']),
        O=mdesc(space=1, base=0xD000, n=0, n_sel=DYN['POS_SLOT1'])))
    R(header('CTL', 'ENDLOOP'))
    # CF-IDXD: IDX.TOPK writes the I table (k ids + count row); expert fetch by id in a LOOP over k (L); n from VM
    R(header('IDX', 'TOPK', param=6), descs=dict(A=mdesc(space=1, base=0xE000, n=256),
                                                 O=mdesc(space=1, fmt=5, base=0xF000, n=6)))
    R(header('CTL', 'LOOP', param=6))
    R(header('SM', 'MATVEC', wait=wIDX, param=3), descs=dict(
        A=mdesc(space=2, n=4096),
        B=mdesc(space=0, fmt=4, indexed=1, base=0x4000_0000, n=4096, m=128, dyn_mul=0x80_0000),
        O=mdesc(space=1, base=0x10000, n=128, lstride=128),
        I=mdesc(space=1, fmt=5, base=0xF000, n=6, stride=16)))
    R(header('CTL', 'ENDLOOP'))
    R(header('DMA', 'LOAD', wait=wIDX), descs=dict(
        A=mdesc(space=0, fmt=2, indexed=1, base=0x8000_0000, n=0, m=1, n_sel=NFV, dyn_mul=0x240),
        O=mdesc(space=1, base=0x12000, n=0, n_sel=NFV),
        I=mdesc(space=1, fmt=5, base=0xF000, n=6, stride=16)))
    # DS full-shape DYN codes 16..40, slot 0..7 (DS window / compressed counts at pos + slot)
    for c in range(16, 41):
        R(header('COLL', 'ALL_GATHER', slot=c % 8, param=0), descs=dict(
            A=mdesc(space=2, base=0x13000 + c, n=0, n_sel=c, dyn_sel=c, dyn_mul=3),
            O=mdesc(space=0, base=0x7000_0000, n=1, dyn_sel=c, dyn_mul=0x1000)))
    R(header('SFU', 'GLU', pred=1, imm_a=0x7F7FFFFF), descs=dict(
        A=mdesc(space=1, base=1), B=mdesc(space=1, base=2), C=mdesc(space=1, ibcast=1, base=3), O=mdesc(space=1, base=4)))
    R(header('HC', 'HC_MIX', pred=2), descs=dict(A=mdesc(space=1, base=5), O=mdesc(space=1, base=6)))
    R(header('ARGMAX', 'LOCAL', wait=0xFFFF & ~1, imm_a=37984), descs=dict(
        A=mdesc(space=2, n=37984), O=mdesc(space=1, base=0x8000, n=2)))
    R(header('CTL', 'FENCE'))
    R(header('CTL', 'END', wait=1 << UNIT['ARGMAX']), descs=dict(A=mdesc(space=1, fmt=5, base=0x8001, n=1)))
    return W


DS_N = {k: 16 + i for i, k in enumerate(['WIN', 'NC1', 'NC2', 'NS1', 'NS2'])}


def fault_programs():
    """small programs that must end with status 3 (the record before the bad one dispatches)"""
    ok = record(header('SU', 'VOP'), sut=0, descs=dict(A=mdesc(space=1, base=0x10, n=4), O=mdesc(space=1, base=0x20, n=4)))
    end = record(header('CTL', 'END', wait=0xFFFE), descs=dict(A=mdesc(space=1, fmt=5, base=0x8001, n=1)))
    P = {}
    P['simt_absent'] = ok + record(header('SIMT', 'RUN', param=5)) + end
    P['rsv_unit13'] = ok + record(header(13, 0)) + end
    P['op_range'] = ok + record(header('SM', 1)) + end
    P['ctl_amax'] = ok + record(header('CTL', 'AMAX')) + end
    tk = lambda base, n, **kw: record(header('CTL', 'TOKX', wait=0xFFFE, **kw), descs=dict(A=mdesc(space=1, fmt=5, base=base, n=n)))  # noqa: E731
    P['tokx_16'] = ok + tk(0x8100, 16) + end
    P['tokx_3_dyn'] = ok + record(header('CTL', 'TOKX', wait=0xFFFE, slot=3), descs=dict(
        A=mdesc(space=1, fmt=5, base=0x8100, n=0, n_sel=DYN['SLOT']))) + end
    P['tokx_twice'] = ok + tk(0x8100, 16) + tk(0x8105, 2) + end
    P['tokx_17'] = ok + tk(0x8100, 17) + end
    P['tokx_0'] = ok + tk(0x8100, 0) + end
    P['tokx_vocab'] = ok + tk(0x8110, 2) + end
    P['tokx_no_A'] = ok + record(header('CTL', 'TOKX')) + end
    P['dyn_rsv9'] = ok + record(header('DMA', 'LOAD'), descs=dict(
        A=mdesc(space=0, base=0, n=4, dyn_sel=9, dyn_mul=1), O=mdesc(space=1, n=4))) + end
    P['dyn_rsv41'] = ok + record(header('DMA', 'LOAD'), descs=dict(
        A=mdesc(space=0, base=0, n=0, n_sel=41), O=mdesc(space=1, n=4))) + end
    P['idx_no_I'] = ok + record(header('DMA', 'LOAD'), descs=dict(
        A=mdesc(space=0, indexed=1, base=0, n=4, dyn_mul=32), O=mdesc(space=1, n=4))) + end
    P['idx_id_range'] = ok + record(header('DMA', 'LOAD'), descs=dict(        # id * dyn_mul beyond 2^40
        A=mdesc(space=0, indexed=1, base=0xFF_FFFF_0000, n=4, dyn_mul=(1 << 27) - 1), O=mdesc(space=1, n=4),
        I=mdesc(space=1, fmt=5, base=0xF000, n=1))) + end
    P['idx_vm_range'] = ok + record(header('CTL', 'LOOP', param=4)) + record(header('DMA', 'LOAD'), descs=dict(
        A=mdesc(space=0, indexed=1, base=0, n=4, dyn_mul=32), O=mdesc(space=1, n=4),
        I=mdesc(space=1, fmt=5, base=(1 << 18) - 2, n=1))) + record(header('CTL', 'ENDLOOP')) + end
    P['nvm_range'] = ok + record(header('DMA', 'LOAD'), descs=dict(
        A=mdesc(space=0, base=0, n=0, n_sel=NFV), O=mdesc(space=1, n=4),
        I=mdesc(space=1, fmt=5, base=0xF0FF, n=1, stride=1))) + end
    P['vm_base_range'] = ok + record(header('SU', 'VOP'), sut=0, descs=dict(
        A=mdesc(space=1, base=(1 << 18) - 4, n=4, lstride=0, dyn_sel=DYN['POS'], dyn_mul=1))) + end
    P['loop0'] = ok + record(header('CTL', 'LOOP', param=0)) + end
    P['loop3'] = ok + record(header('CTL', 'LOOP', param=2)) + record(header('CTL', 'LOOP', param=(1 << 16) | 2)) + \
        record(header('CTL', 'LOOP', param=2)) + end
    P['loop_samelvl'] = ok + record(header('CTL', 'LOOP', param=2)) + record(header('CTL', 'LOOP', param=2)) + end
    P['endloop_only'] = ok + record(header('CTL', 'ENDLOOP')) + end
    P['end_no_A'] = ok + record(header('CTL', 'END', wait=0xFFFE))
    P['end_tok_vocab'] = ok + record(header('CTL', 'END', wait=0xFFFE), descs=dict(A=mdesc(space=1, fmt=5, base=0x8002, n=1)))
    P['end_tok_ok'] = ok + record(header('CTL', 'END', wait=0xFFFE), descs=dict(A=mdesc(space=1, fmt=5, base=0x8003, n=1)))
    big = []
    for q in range(40):        # a 600-word loop body: larger than the 512-word ring
        big += record(header('SU', 'VOP'), sut=q, descs={k: mdesc(space=1, base=q, n=1) for k in OPND[:7]})
    P['ring_overflow'] = ok + record(header('CTL', 'LOOP', param=2)) + big + record(header('CTL', 'ENDLOOP')) + end
    return P


def main():
    rng = random.Random(20261009)
    words, cases, meta = [], [], {}
    VM0 = {0x8001: 4242, 0x8002: 151936, 0x8003: 151935, 0xF100: 1 << 21, 0xF000: 3}
    VM0.update({0x8100 + q: 1000 * q + 7 for q in range(16)})
    VM0.update({0x8110: 5, 0x8111: 151936})

    def add_prog(name, w):
        meta[name] = (len(words), len(w))
        words.extend(w)
        return meta[name][0]

    # 1. Qwen3-8B token program (CF-PROG, against the simulator's addressing)
    qw, qrecs, g, md = qwen_program()
    qe = add_prog('qwen', qw)
    tok_q = 9707
    tok_out = 77777

    def qwen_disp(k, u, o):
        return [(g.vm['TOK'], tok_out)] if (u, o) in (('COLL', 'ARGMAX_MERGE'), ('ARGMAX', 'LOCAL')) else []
    # 2. synthetic CF-LOOP2 / CF-IDXD / DS DYN program, and its stale-table negative
    se = add_prog('synth', synth_program(random.Random(5)))
    sse = add_prog('synth_stale', synth_program(random.Random(5), stale=True))
    ids = [7, 0, 63, 12, 5, 1000]

    def synth_disp(k, u, o):
        if (u, o) == ('IDX', 'TOPK'):
            return [(0xF000 + i, v) for i, v in enumerate(ids)] + [(0xF000 + 16 + i, 100 + 7 * i) for i in range(6)]
        if (u, o) == ('ARGMAX', 'LOCAL'):
            return [(0x8001, 131071)]
        return []
    fps = {n: add_prog(n, w) for n, w in fault_programs().items()}
    assert len(words) < (1 << 16)
    Q = dict(vocab=151936, ctxmax=40960)
    D = dict(vocab=129280, ctxmax=1 << 20)
    plan = [('qwen_p8191_r1', qe, tok_q, 8191, 1, Q, qwen_disp, False),
            ('qwen_p0_r3', qe, 151935, 0, 3, Q, qwen_disp, False),
            ('synth_ds_p1048575_r2', se, 3, (1 << 20) - 1, 2, D, synth_disp, False),
            ('synth_ds_p20_r0', se, 129279, 20, 0, D, synth_disp, False),
            ('synth_ds_p777_r3', se, 5, 777, 3, D, synth_disp, False),
            ('synth_qwen_p0', se, 131072, 0, 1, Q, synth_disp, False)]
    plan += [(n, e, 1, 100, 0, Q, lambda k, u, o: [], False) for n, e in fps.items()]
    plan += [('db_token_range', qe, 151936, 5, 0, Q, qwen_disp, False),
             ('db_pos_range', qe, 1, 40960, 0, Q, qwen_disp, False),
             ('db_ds_token_range', se, 129280, 5, 0, D, synth_disp, False),
             ('unit_fault', se, 3, 9, 0, D, synth_disp, False)]
    stale = [('stale_table', sse, 3, 9, 0, D, synth_disp, True)]
    out_cases, exp_lines, stale_exp = [], [], []
    for (name, entry, tok, pos, rank, lim, disp, _), dst in [(p, exp_lines) for p in plan] + [(p, stale_exp) for p in stale]:
        ref = Ref(words, entry, tok, pos, rank, lim['vocab'], lim['ctxmax'], VM0, disp)
        tr, cpl = ref.run()
        fault_at = 3 if name == 'unit_fault' else 0xFFFF
        if name == 'unit_fault':
            tr, cpl = tr[:4], (0, 1)        # the 4th dispatch's unit reports a fault on retire -> status 1
        if name.startswith('qwen_p') and cpl[1] == 0:
            sim_check(words, entry, tr, qrecs, pos, tok, rank)
        vmw = []
        for k, d in enumerate(tr):
            for a, v in disp(k, UNITS[d['unit']], OPS[UNITS[d['unit']]][field(d['hdr'], UOP, 'op')]):
                vmw.append((len(dst) // 11 + k, a, v))
        c = dict(name=name, entry=entry, token=tok, pos=pos, rank=rank, vocab=lim['vocab'], ctxmax=lim['ctxmax'],
                 ndisp=len(tr), cpl=cpl, fault_at=fault_at, first=len(dst) // 11, vmw=vmw,
                 fault=getattr(ref, 'fault', None), toks=list(ref.toks) if cpl[1] == 0 else [])
        for d in tr:
            meta_w = d['unit'] | d['L'] << 4 | d['L1'] << 20 | (d['pos1'] & M21) << 36 | (d['pslot1'] & M21) << 57
            dst += [meta_w, d['hdr'], d['sut']] + d['eff'] + [sum((n & M21) << (21 * j) for j, n in enumerate(d['n']))]
        (out_cases if dst is exp_lines else stale_cases_list).append(c) if False else None
        c['set'] = 'stale' if dst is stale_exp else 'main'
        out_cases.append(c)
    T = ROOT / 'rtl/hbm_accel/generic/tb'
    (T / 'hgi_seq_image.mem').write_text('\n'.join(f'{w:032X}' for w in words) + '\n')
    for tag, lines in (('', exp_lines), ('_stale', stale_exp)):
        (T / f'hgi_seq_expect{tag}.mem').write_text('\n'.join(f'{x:064X}' for x in lines) + '\n')
        cs = [c for c in out_cases if c['set'] == ('stale' if tag else 'main')]
        cfg = []
        for c in cs:
            cfg.append(' '.join(f'{v:08X}' for v in (c['entry'], c['token'], c['pos'], c['rank'], c['vocab'], c['ctxmax'],
                                                    c['ndisp'], c['cpl'][0], c['cpl'][1], c['fault_at'], c['first'],
                                                    len(c['toks']))))
        mds = []
        for c in cs:     # the case's model descriptor (CP mode: loaded through the CFG window + CFG_COMMIT)
            mds += G.d_pack(dict(magic=G.MAGIC, ver_minor=G.D_VERSION[1], ver_major=G.D_VERSION[0], n_words=G.NWORDS,
                                 cp_vocab=c['vocab'], cp_ctx_max=c['ctxmax'],
                                 coll_group_size=96 if c['vocab'] == 129280 else 4, entry_ar=c['entry'],
                                 image_base=0x10, image_pages=1))
        (T / f'hgi_seq_md{tag}.mem').write_text('\n'.join(f'{x:08X}' for x in mds) + '\n')
        (T / f'hgi_seq_toks{tag}.mem').write_text('\n'.join(' '.join(f'{x:08X}' for x in (c['toks'] + [0] * 16)[:16])
                                                           for c in cs) + '\n')
        (T / f'hgi_seq_cfg{tag}.mem').write_text('\n'.join(cfg) + '\n')
        vmw = [w for c in cs for w in c['vmw']]
        (T / f'hgi_seq_vmw{tag}.mem').write_text('\n'.join(f'{k:08X}{a:08X}{v:08X}' for k, a, v in vmw) + '\n')
        print(tag or 'main', len(cs), 'cases', len(lines) // 11, 'dispatches', len(vmw), 'VM writes')
    (T / 'hgi_seq_vm0.mem').write_text('\n'.join(f'{a:08X}{v:08X}' for a, v in sorted(VM0.items())) + '\n')
    hdr = '\n'.join(f'localparam integer {k} = {v};' for k, v in dict(
        SEQ_NW=len(words), SEQ_NCASE=sum(c['set'] == 'main' for c in out_cases),
        SEQ_NCASE_STALE=sum(c['set'] == 'stale' for c in out_cases), SEQ_NEXP=len(exp_lines),
        SEQ_NEXP_STALE=len(stale_exp), SEQ_NVM0=len(VM0)).items())
    (T / 'hgi_seq_sizes.svh').write_text('// GENERATED by tools/hgi_seq_vectors.py\n' + hdr + '\n')
    ds_check = None
    try:
        import v41_fullshape_isa as F
        import hdc_isa_v41 as I
        bad = 0
        for p in (0, 1, 7, 127, 128, 129, 1000, 16383, 16384, 65535, 1 << 19, (1 << 20) - 1):
            for r in (0, 1, 2, 3):
                fd = F.full_dyn(p, 0, r)
                mine = ds_full(p, r)
                bad += sum(fd[s] != mine[i] for i, s in enumerate(I.FULL_DYN.values()))
        ds_check = dict(positions=12, ranks=4, mismatches=bad)
    except Exception as e:  # noqa: BLE001
        ds_check = dict(error=repr(e)[:200])
    (T / 'hgi_seq_vectors.json').write_text(json.dumps(dict(
        schema='opentallas.hgi_seq_vectors.v2', spec='HGI-1 v1.0 normative (docs/HBM_GENERIC_INTERFACE.md, '
        'results/arch/hbm_generic_iface_20261009/spec.json)', words128=len(words), ring_words=RW,
        programs={k: dict(entry=v[0], words=v[1]) for k, v in meta.items()},
        qwen_program=dict(records=len(qrecs), source='tools/hgi_sim/qwen_compiler.program (P 8192, 36 layers, '
                          'embed + layers + head), effective bases and n checked against hgi_sim Machine.eff'),
        ds_full_dyn_vs_v41_fullshape=ds_check,
        cases=[{k: c[k] for k in ('name', 'set', 'entry', 'token', 'pos', 'rank', 'vocab', 'ctxmax', 'ndisp', 'cpl',
                                  'fault')} for c in out_cases]), indent=1) + '\n')
    for c in out_cases:
        print(f"{c['name']:24s} {c['set']:5s} disp {c['ndisp']:5d} cpl {c['cpl']} {c['fault'] or ''}")
    print('DS full-dyn check vs v41_fullshape_isa:', ds_check)


stale_cases_list = []

if __name__ == '__main__':
    main()
