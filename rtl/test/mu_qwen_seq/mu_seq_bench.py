#!/usr/bin/env python3
"""MU-QWEN-SEQ bench (2026-10-18): qfd_dv_cmd_cal_mu, the multi-user (NU playheads) successor of the DV compute die's
static command calendar qfd_dv_cmd_cal (the run side of the die's tensor-group sequencer).

    mu_seq_bench.py --work DIR [--mut M] [--verilator PATH] [--jobs N]

One shared calendar image (one decode-layer segment with 2 all-reduce epochs, plus token-start / LM-head / boot segments)
is loaded over the PW/DW face exactly as qfd_sys_face loads it.  Scenarios:
  lock   NU 1 in LOCKSTEP with the unmodified qfd_dv_cmd_cal (every output, every edge): user 0's 3-period schedule, a
         token-start and an LM-head stage, a start while playing (fault), a reload while playing (fault), a clean
         reload and a replay.  -> mismatches must be 0.
  solo1  NU 1 (lockstep binary), user 0 only, 3 periods          solo4  NU 4, user 0 only, the same events
  mu4    NU 4, users 0..3 started at the compiled shifts 0 / 1,722 / 3,443 / 5,165 of the 6,886-cycle period, 3 periods
  busy4  NU 4, user 1 restarted while its segment plays          -> fault_code[0] must rise
  coll4  NU 4, users 0 and 2 started 4 edges apart (entries on the same edges) -> fault_code[1] must rise
Checks (PASS needs all):
  C1 lockstep mismatches 0;  C2 solo1 and solo4 fault-free;  C3 user 0's events (CMD / SUI / XCI / EMB / SEG / DONE,
  absolute cycles and words) in mu4 == solo4 == solo1;  C4 mu4 fault-free, every user's events == the image's entries
  at S_start + T_k + C with the user's relocation (PORTS bases + u x UVM_STRIDE, STN VM dbase + u x UVM_STRIDE, SU pidx +
  u x PIDX_STRIDE, XC tag user field = u), one DONE per start;  C5 behavioural static collective + slice landing on
  mu4's command stream: engine accepts a command per `words` edges (else conflict), first result FIRST_RX edges after
  the XC, then one word every RX_STRIDE edges, results = f(tag, k) (tag carries the user); each word lands at the slice's
  PORTS ar_base + 16 k (ar_k reset by PORTS, as qfd_dv_slice2) and must land at user(tag)'s own region + 16 k;
  C6 busy4 sets fault_code[0];  C7 coll4 sets fault_code[1].
Mutants (--mut, each must FAIL): 4 TLOAD payload halves swapped, 5 TLOAD word one edge late (C1 lockstep / C8), 11 relocation/tag from the wrong user, 12 per-user base dropped, 13 old one-in-flight
rule, 14 start-while-busy not faulted, 15 a start freezes every playhead (the single calendar's global gating).
33 (MU-DQ-CALPIPE2) the precomputed next head on a pop takes FIFO slot rp instead of rp + 1.
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCES = ['rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv', 'rtl/qwen_dv/qfd_dv_cmd_cal.sv',
           'rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv',
           'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']
TB = HERE / 'tb_mu_cmd_cal.sv'
UVM_STRIDE, PIDX_STRIDE, UTAG_LSB = 0x4000, 64, 6   # per-user region 16 KiB words: AR 0x1000..0x1800, DD 0x2000, EM 0x3000 stay inside
PERIOD, SHIFTS, NPER = 6886, [0, 1722, 3443, 5165], 3
FIRST_RX, RX_STRIDE = 1928, 4          # behavioural TP8 all-reduce: XC -> first result word, result spacing
BASE = 64                              # image entry base (PW word)


# ------------------------------------------------------------------------------------------------ image
def F(**kv):
    """cmd word from (lsb, width, value) fields."""
    w = 0
    for _, (lsb, wid, val) in kv.items():
        assert 0 <= val < (1 << wid), (lsb, wid, val)
        w |= val << lsb
    return w


def su(p):            return F(go=(0, 1, 1), kind=(1, 3, 1), pidx=(4, 9, p), dst=(112, 4, 15))
def stn(dbase, vm=1): return F(go=(0, 1, 1), kind=(1, 3, 2), mode=(4, 2, 0), nw=(7, 8, 16), dst2=(24, 2, vm), db=(26, 24, dbase), dst=(112, 4, 15))
def ports(ar, dd, em): return F(go=(0, 1, 1), kind=(1, 3, 4), ar=(4, 24, ar), dd=(28, 24, dd), aren=(52, 1, 1), dden=(53, 1, 1), em=(54, 24, em), dst=(112, 4, 15))
def xc(seg, words, mode=0): return F(go=(0, 1, 1), kind=(1, 3, 0), sub=(4, 2, 0), mode=(6, 1, mode), words=(7, 16, words), tag=(23, 32, seg), dst=(112, 4, 15))
def loc_emb():        return F(go=(0, 1, 1), kind=(1, 3, 1), dst=(112, 4, 14))
def loc_seg(b):       return F(go=(0, 1, 1), kind=(1, 3, 2), base=(4, 12, b), dst=(112, 4, 14))
def tload(row, kind, dst, src, ea, tag):   # MU-QW-DIE 10-19: LOCAL kind 3 TLOAD (QLB-C4b), block row = PW 16 row .. +15
    return F(go=(0, 1, 1), kind=(1, 3, 3), row=(4, 6, row), tk=(10, 3, kind), tdst=(13, 4, dst), tsrc=(17, 4, src),
             ea=(21, 24, ea), tag=(45, 28, tag), dst=(112, 4, 14))
TL_ROW = 60
TLOADS = [(TL_ROW, 3, 5, 1, 0x10, 7), (TL_ROW, 1, 9, 2, 0x123, 0xABCDE)]
def tl_word(row, kind, dst, src, ea, tag, pw):
    ctl = (1 << 63) | (kind << 60) | (dst << 56) | (src << 52) | (ea << 28) | tag
    pay = sum(pw[16 * row + i] << (64 * i) for i in range(16))
    return (ctl << 1024) | pay
def setid():          return F(go=(0, 1, 1), kind=(1, 3, 7), dst=(112, 4, 15))


AR_WORDS = 64
AR_REG = {0: 0x1000, 1: 0x1400}       # image ar_base of the two epochs (user 0); user u adds u x UVM_STRIDE
SEGS = {
    # decode layer: 2 all-reduce epochs; PORTS 8 edges before the epoch's first result (after the previous epoch's last)
    1: [(8, su(1)), (12, su(2)), (16, stn(0x100)), (60, su(3)), (400, xc(0, AR_WORDS)), (1200, su(4)),
        (2320, ports(AR_REG[0], 0x2000, 0x3000)), (2600, su(5)), (2640, stn(0x140)), (2700, xc(1, AR_WORDS)),
        (3000, loc_seg(0x10)), (4620, ports(AR_REG[1], 0x2000, 0x3000)), (4900, su(6)), (5000, su(7))],
    0: [(8, loc_emb()), (12, su(8)), (20, su(9))],                               # token start (stage 0)
    2: [(8, stn(0x180)), (16, loc_seg(0x20)), (24, xc(2, 1, mode=1))],          # LM head (stage 37)
    3: [(4, setid()), (8, su(10)), (12, tload(*TLOADS[0])), (14, tload(*TLOADS[1]))],   # BOOT (+ 2 TLOAD, QLB-C4b)
}


def image():
    order, entries, desc = [1, 0, 2, 3], [], {}
    for s in order:
        while len(entries) % 4: entries.append((1 << 116) * 1)   # pad (never played): delta 1 NOP
        first = len(entries)
        t = 0
        for T, c in SEGS[s]:
            d = T - t; t = T
            assert 1 <= d <= 4095
            entries.append((d << 116) | c)
        desc[s] = (first, len(SEGS[s]))
    nent = len(entries)
    assert BASE + 2 * nent <= 976
    pw = [0] * 1024
    for e, v in enumerate(entries):
        pw[BASE + 2 * e] = v & ((1 << 64) - 1); pw[BASE + 2 * e + 1] = v >> 64
    for i in range(16):                    # the TLOAD block (above the entry area, below the control rows)
        pw[16 * TL_ROW + i] = (0x9E3779B97F4A7C15 * (i + 1)) & ((1 << 64) - 1)
    dw = [(0x43414c44 << 32) | (BASE << 16) | nent] + [(desc[s][0] << 16) | desc[s][1] for s in range(4)] + [0, 0, 0]
    return pw, dw


def load_events(c0):
    pw, dw = image()
    ev = [(c0 + a, 0, (a << 64) | pw[a]) for a in range(1024)]
    ev += [(c0 + 1024 + a, 1, (a << 64) | dw[a]) for a in range(8)]
    return ev


def start(c, user, stage): return (c, 2, (user << 6) | stage)


# ------------------------------------------------------------------------------------------------ run
def build(work, vl, nu, mut, lock, jobs):
    d = work / f'b_nu{nu}_m{mut}_l{lock}'
    exe = d / 'Vtb_mu_cmd_cal'
    if exe.exists(): return exe
    cmd = [vl, '--binary', '--timing', '-O2', '-j', str(jobs), '-Wno-fatal', '-Wno-lint', '-Wno-style', '-Wno-TIMESCALEMOD',
           '-Wno-WIDTHCONCAT', '--x-assign', '0', '--x-initial', '0', '--top-module', 'tb_mu_cmd_cal',
           f'-GNU={nu}', f'-GMUT={mut}', f'-GLOCKSTEP={lock}', f'-GUVM_STRIDE={UVM_STRIDE}', f'-GPIDX_STRIDE={PIDX_STRIDE}',
           '-Mdir', str(d)] + [str(ROOT / s) for s in SOURCES] + [str(TB)]
    d.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    (d / 'build.log').write_text(r.stdout + r.stderr)
    if r.returncode != 0 or not exe.exists():
        sys.exit(f'BUILD FAILED nu{nu} m{mut} l{lock}: see {d}/build.log\n' + (r.stdout + r.stderr)[-3000:])
    return exe


def run(work, exe, name, events, ncyc):
    events = sorted(events, key=lambda e: (e[0], e[1]))
    evf, lg = work / f'{name}.ev', work / f'{name}.log'
    evf.write_text(''.join(f'{c} {k} {v:x}\n' for c, k, v in events))
    r = subprocess.run([str(exe), f'+EV={evf}', f'+LOG={lg}', f'+NCYC={ncyc}'], capture_output=True, text=True)
    if r.returncode != 0: sys.exit(f'RUN FAILED {name}: {r.stdout[-2000:]} {r.stderr[-2000:]}')
    out = dict(ev=[], faults=[], mism=None, end=None)
    for ln in lg.read_text().split('\n'):
        p = ln.split()
        if not p: continue
        c, k = int(p[0]), p[1]
        if k in ('CMD', 'SUI', 'SEG'): out['ev'].append((c, k, int(p[2]), int(p[3], 16)))
        elif k in ('XCI', 'EMB', 'DONE'): out['ev'].append((c, k, int(p[2]), 0))
        elif k == 'TL': out.setdefault('tl', []).append((c, int(p[2]), int(p[3], 16)))
        elif k == 'FAULT': out['faults'].append((c, p[2]))
        elif k == 'END': out['end'] = (int(p[2]), p[3]); out['mism'] = int(p[4])
    return out


# ------------------------------------------------------------------------------------------------ expectations
def reloc(c, u):
    kind, dst = (c >> 1) & 7, (c >> 112) & 15
    if u == 0 or dst == 14: return c
    def put(w, lsb, wid, v):
        assert v < (1 << wid); return (w & ~(((1 << wid) - 1) << lsb)) | (v << lsb)
    def get(w, lsb, wid): return (w >> lsb) & ((1 << wid) - 1)
    ub = u * UVM_STRIDE
    if kind == 4:
        for lsb in (4, 28, 54): c = put(c, lsb, 24, get(c, lsb, 24) + ub)
    elif kind == 2 and (c >> 24) & 1: c = put(c, 26, 24, get(c, 26, 24) + ub)
    elif kind == 1: c = put(c, 4, 9, get(c, 4, 9) + u * PIDX_STRIDE)
    elif kind == 0 and get(c, 4, 2) == 0: c = put(c, 23 + UTAG_LSB, 2, u)
    return c


def expected_user_events(entries, u, s_cyc, C):
    ev = []
    for T, c in entries:
        t = s_cyc + T + C
        dst, kind = (c >> 112) & 15, (c >> 1) & 7
        if dst == 14:
            if kind == 1: ev.append((t, 'EMB', u, 0))
            else: ev.append((t, 'SEG', u, (c >> 4) & 0xfff))
        else:
            w = reloc(c, u)
            ev.append((t, 'CMD', u, w))
            if kind == 1: ev.append((t, 'SUI', u, (w >> 4) & 0x1ff))
            if kind == 0: ev.append((t, 'XCI', u, 0))
    ev.append((s_cyc + entries[-1][0] + C, 'DONE', u, 0))
    return ev


def landing_model(evs):
    """behavioural static TP8 collective + slice AR landing on the issued command stream; returns error list."""
    errs, acts = [], []
    eng_free = -1
    for c, k, u, w in evs:
        if k != 'CMD': continue
        kind = (w >> 1) & 7
        if kind == 4: acts.append((c, 0, 'P', (w >> 4) & 0xffffff))
        if kind == 0 and ((w >> 4) & 3) == 0 and not ((w >> 6) & 1):
            words, tag = (w >> 7) & 0xffff, (w >> 23) & 0xffffffff
            if c < eng_free: errs.append(f'{c}: engine conflict (command while the slot sequencer is busy)')
            eng_free = c + words
            for i in range(words):
                acts.append((c + FIRST_RX + RX_STRIDE * i, 1, 'R', (tag, i)))
    ar_base, ar_k, landed = None, 0, {}
    for t, _, a, v in sorted(acts):
        if a == 'P': ar_base, ar_k = v, 0; continue
        tag, i = v
        user, seg = (tag >> UTAG_LSB) & 3, tag & 0x3f
        want = user * UVM_STRIDE + AR_REG[seg] + 16 * i
        got = None if ar_base is None else ar_base + 16 * ar_k
        ar_k += 1
        val = (tag * 2654435761 + i * 40503) & 0xffffffff
        if got != want: errs.append(f'{t}: user {user} AR{seg} word {i} landed at {got} want {want}')
        landed[(t, user, seg, i)] = val
    return errs, len(landed)


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True); ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--verilator', default=os.environ.get('VERILATOR', 'verilator')); ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    m = a.mut
    e1 = build(work, a.verilator, 1, m, 1, a.jobs)
    e4 = build(work, a.verilator, 4, m, 0, a.jobs)
    c0, s0 = 2, 1100                       # image load at 2..1033, boot plays at the seal; first start at s0
    ld = load_events(c0)
    starts0 = [s0 + p * PERIOD for p in range(NPER)]
    solo_ev = ld + [start(starts0[p], 0, p + 1) for p in range(NPER)]
    end_solo = s0 + NPER * PERIOD + 400
    res, fails = {}, []
    # lockstep stimulus: user 0's schedule + token start / LM head + faults + reload + replay
    t = end_solo
    lock_ev = list(solo_ev) + [start(t, 0, 0), start(t + 100, 0, 37), start(t + 200, 0, 5), start(t + 230, 0, 5)]
    lock_ev += [(t + 700, 0, 0)]                                   # PW0 (a new image) while the stage-5 segment plays
    t3 = t + 6000
    lock_ev += load_events(t3) + [start(t3 + 1100, 0, 2)]           # clean reload when idle, then a replay
    res['lock'] = run(work, e1, 'lock', lock_ev, t3 + 1100 + 5400)
    res['solo1'] = run(work, e1, 'solo1', solo_ev, end_solo)
    res['solo4'] = run(work, e4, 'solo4', solo_ev, end_solo)
    mu_starts = [(s0 + p * PERIOD + SHIFTS[u], u, p + 1) for p in range(NPER) for u in range(4)]
    res['mu4'] = run(work, e4, 'mu4', ld + [start(c, u, st) for c, u, st in mu_starts], end_solo + SHIFTS[-1])
    res['busy4'] = run(work, e4, 'busy4', ld + [start(s0, 1, 1), start(s0 + 2000, 1, 2)], s0 + 8000)
    res['coll4'] = run(work, e4, 'coll4', ld + [start(s0, 0, 1), start(s0 + 4, 2, 1)], s0 + 6000)

    # C1 lockstep
    if res['lock']['mism'] != 0 or res['solo1']['mism'] != 0:
        fails.append(f"C1 lockstep mismatches lock {res['lock']['mism']} solo1 {res['solo1']['mism']}")
    # C2 solo fault-free
    for n in ('solo1', 'solo4'):
        if res[n]['faults']: fails.append(f'C2 {n} faulted: {res[n]["faults"]}')
    # C3 user 0 identity
    u0 = lambda r: [e for e in r['ev'] if e[2] == 0 and e[0] >= s0]
    if u0(res['solo1']) != u0(res['solo4']): fails.append('C3 user 0 events differ: solo4 vs solo1 (NU 1)')
    if u0(res['solo1']) != u0(res['mu4']):
        d = [x for x in u0(res['mu4']) if x not in u0(res['solo1'])][:3] + [x for x in u0(res['solo1']) if x not in u0(res['mu4'])][:3]
        fails.append(f'C3 user 0 events differ: mu4 vs solo1 (first diffs {d})')
    # C4 every user's timeline
    cmds = [e for e in res['solo1']['ev'] if e[1] == 'CMD' and e[0] >= s0]
    C = cmds[0][0] - s0 - SEGS[1][0][0] if cmds else 0
    if res['mu4']['faults']: fails.append(f'C4 mu4 faulted: {res["mu4"]["faults"]}')
    got = sorted(e for e in res['mu4']['ev'] if e[0] >= s0)
    want = sorted(x for c, u, st in mu_starts for x in expected_user_events(SEGS[1], u, c, C))
    if got != want:
        miss = [x for x in want if x not in got][:3]; extra = [x for x in got if x not in want][:3]
        fails.append(f'C4 mu4 timeline != compiled (missing {len(set(want) - set(got))} e.g. {miss}; extra {len(set(got) - set(want))} e.g. {extra})')
    per_user = {u: sum(1 for e in got if e[1] == 'DONE' and e[2] == u) for u in range(4)}
    # C5 landing
    lerr, nland = landing_model(got)
    if lerr: fails.append(f'C5 landing: {len(lerr)} errors, first {lerr[:3]}')
    if nland != 4 * NPER * 2 * AR_WORDS: fails.append(f'C5 landed {nland} words, want {4 * NPER * 2 * AR_WORDS}')
    # C8 (MU-QW-DIE 10-19) TLOAD: every image seal plays the BOOT TLOAD words on tl (user 0), payload = the PW block
    pw_img, _ = image()
    want_tl = [tl_word(*t, pw_img) for t in TLOADS]
    for n, loads in (('lock', 2), ('mu4', 1)):
        g = [w for c, u, w in res[n].get('tl', [])]
        if g != want_tl * loads:
            fails.append(f'C8 {n} TLOAD words {len(g)} != expected {len(want_tl) * loads} (or payload / header differs)')
    # C6 / C7 negative scenarios
    fc = lambda r: r['end'][1] if r['end'] else '000000'
    if fc(res['busy4'])[-1] != '1': fails.append(f"C6 busy4 restart not faulted (fault_code {fc(res['busy4'])})")
    if fc(res['coll4'])[-2] != '1': fails.append(f"C7 coll4 collision not faulted (fault_code {fc(res['coll4'])})")
    # C9 SRAM ring: one command/edge, both four-entry row boundaries, ring
    # wrap and partial final row. Reload between scenarios to exercise initial
    # pending-write forwarding too. Run each NU4 playhead independently so a
    # deliberate shared-port collision cannot hide a storage error.
    old_seg = SEGS[1]
    dense = [(8 + i, su(1 + i)) for i in range(23)]
    SEGS[1] = dense
    dense_count = 0
    for nu, exe in ((1, e1), (4, e4)):
        for user in range(nu):
            ds = run(work, exe, f'dense_nu{nu}_u{user}', load_events(c0) + [start(s0, user, 1)], s0 + 100)
            actual = sorted(e for e in ds['ev'] if e[0] >= s0)
            expected = sorted(expected_user_events(dense, user, s0, C))
            if ds['faults'] or actual != expected or (nu == 1 and ds['mism'] != 0):
                fails.append(f'C9 SRAM dense nu{nu} u{user}: faults={ds["faults"]}, '
                             f'missing={len(set(expected)-set(actual))}, extra={len(set(actual)-set(expected))}, '
                             f'lockstep={ds["mism"]}')
            dense_count += len(actual)
    dense_busy = run(work, e1, 'dense_busy', load_events(c0) + [start(s0, 0, 1), start(s0 + 11, 0, 1)], s0 + 100)
    if dense_busy['mism'] != 0:
        fails.append(f'C9 SRAM refused-start lockstep={dense_busy["mism"]}')
    SEGS[1] = old_seg
    summ = dict(dense_events=dense_count, mut=m, verdict='PASS' if not fails else 'FAIL', fails=fails, C_issue_offset=C,
                lock=dict(mismatches=res['lock']['mism'], faults=res['lock']['faults']),
                solo1_events=len(u0(res['solo1'])), mu4_events=len(got), mu4_done_per_user=per_user,
                landed_words=nland, busy4_fault_code=fc(res['busy4']), coll4_fault_code=fc(res['coll4']),
                mu4_fault_code=fc(res['mu4']))
    (work / f'summary_m{m}.json').write_text(json.dumps(summ, indent=1))
    print(f"MU_SEQ_{summ['verdict']} mut {m}" + ('' if not fails else ': ' + ' | '.join(fails)))
    print(json.dumps({k: v for k, v in summ.items() if k != 'fails'}))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
