#!/usr/bin/env python3
"""MU-ADOPT-CTLM bench (2026-10-19): qfd_dv_cmd_cal_mu adopted into the DV compute-die control cluster qfd_tt_ctlm_dv
(u_cal, NU 4, UFOLD 1, strides = tools/qwen_static_schedule/mu_calendar.py DV_*), driven through the cluster's real
faces (tt pw + seq_dh program copies, dh run levels + the new dh_user input), HARD_HR 1 (the h16c/h17 head RTL).

    mu_ctlm_bench.py --work DIR [--mut M] [--verilator PATH] [--jobs N]

One shared calendar image (user-0 absolute fields, every user field 0): token start (stage 0: LOCAL EMB + SU), decode
layer (stage 1..3: SU / STN-VM / PORTS / 2 XC epochs / LOCAL SEG), LM head (stage 37: AMAX clear, STN armed, LOCAL SEG,
XC ARX mode 1, AMAX emit), BOOT (SETID).  Scenarios:
  solo1  NU 1, user 0 only: token start, 3 decode layers, LM head
  solo4  NU 4, the same events (user 0 only)
  mu4    NU 4, users 0..3, each with its own token / position, every user's segments at the compiled shifts
         0 / 1,722 / 3,443 / 5,165 of the 6,886-cycle period: the four users' segments overlap (up to 4 playing at once)
Checks (PASS needs all):
  C1 solo1 / solo4 / mu4 calendar fault-free, start_fault 0;
  C2 latency user identity: user 0's CMD / EMB / SEG / MES events AND the head-side outputs (hr, native_cmd / tok / pos,
     command_stage, layer_context_v, control_stores_ready, program_obs, cf: every change, absolute cycle) and the head's
     SU accepted count are identical in solo1, solo4 and mu4;
  C3 every user's commands == the image's entries at S + T_k + C with the user carried in the word: PORTS / STN-VM bases
     + u x UVM_STRIDE, SU pidx + u x PIDX_STRIDE, XC tag bits [23+6 +: 2] = u, STN cmd[52:51] = u, AMAX cmd[9:8] = u
     (the R4 qfd_dv_amax_mu fields);
  C4 per-user token / position: every user's LOCAL EMB sends ITS token; every LOCAL SEG starts the ME segment with ITS
     token / position and base; the ME programme (MES) starts only on user 0's decode-stage starts.
Mutants (--mut, each must FAIL): 16 UFOLD off (STN / AMAX user fields stay 0), 17 head SU count of every user, 18 one
shared tok / pos register, 19 every user's dh start starts the ME programme, 20 head stage latched on every dh start and
not on LOCAL SEG (the single-user wiring).
  C5 head running stage (STAGE_ME 1 ROM relocation): after every ME start command_stage = that segment's user's stage.  (The calendar's own relocation mutants
11..15 are covered by run_mu_seq.sh on qfd_dv_cmd_cal_mu.)
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TB = HERE / 'tb_mu_ctlm_dv.sv'
SRCF = ROOT / 'rtl/test/qwen_dv/tt_ctlm_dv_sources.f'
UVM_STRIDE, PIDX_STRIDE, UTAG_LSB = 4096, 128, 6      # = mu_calendar.DV_UVM_STRIDE / DV_PIDX_STRIDE / DV_UTAG_LSB
PERIOD, SHIFTS, NPER = 6886, [0, 1722, 3443, 5165], 3
BASE = 64


def F(**kv):
    w = 0
    for _, (lsb, wid, val) in kv.items():
        assert 0 <= val < (1 << wid), (lsb, wid, val)
        w |= val << lsb
    return w


def su(p):            return F(go=(0, 1, 1), kind=(1, 3, 1), pidx=(4, 9, p), dst=(112, 4, 15))
def stn(dbase, vm=1, amax=0): return F(go=(0, 1, 1), kind=(1, 3, 2), mode=(4, 2, 0), nw=(7, 8, 16), dst2=(24, 2, vm), db=(26, 24, dbase), am=(50, 1, amax), dst=(112, 4, 15))
def ports(ar, dd, em): return F(go=(0, 1, 1), kind=(1, 3, 4), ar=(4, 24, ar), dd=(28, 24, dd), aren=(52, 1, 1), dden=(53, 1, 1), em=(54, 24, em), dst=(112, 4, 15))
def xc(seg, words, mode=0): return F(go=(0, 1, 1), kind=(1, 3, 0), sub=(4, 2, 0), mode=(6, 1, mode), words=(7, 16, words), tag=(23, 32, seg), dst=(112, 4, 15))
def amax(clr=0, emit=0): return F(go=(0, 1, 1), kind=(1, 3, 6), clr=(4, 1, clr), emit=(5, 1, emit), dst=(112, 4, 15))
def loc_emb():        return F(go=(0, 1, 1), kind=(1, 3, 1), dst=(112, 4, 14))
def loc_seg(b):       return F(go=(0, 1, 1), kind=(1, 3, 2), base=(4, 12, b), dst=(112, 4, 14))
def setid():          return F(go=(0, 1, 1), kind=(1, 3, 7), dst=(112, 4, 15))


# user-0 footprint inside [0, UVM_STRIDE) VM words and [0, PIDX_STRIDE) pidx (the compiler rule)
SEGS = {
    1: [(8, su(1)), (12, su(2)), (16, stn(0x100)), (60, su(3)), (400, xc(0, 64)), (1200, su(4)),
        (2320, ports(0x400, 0x800, 0xC00)), (2600, su(5)), (2640, stn(0x140, vm=2)), (2700, xc(1, 64)),
        (3000, loc_seg(0x10)), (4620, ports(0x600, 0x800, 0xC00)), (4900, su(6)), (5000, su(7))],
    0: [(8, loc_emb()), (12, su(8)), (20, su(9))],                                               # token start
    2: [(8, amax(clr=1)), (12, stn(0x180, amax=1)), (16, loc_seg(0x20)), (24, xc(2, 1, mode=1)), (40, amax(emit=1))],
    3: [(4, setid()), (8, su(10))],                                                              # BOOT
}
STAGE_SEG = lambda st: 0 if st == 0 else 2 if st == 37 else 1


def image():
    order, entries, desc = [1, 0, 2, 3], [], {}
    for s in order:
        while len(entries) % 4: entries.append(1 << 116)
        first, t = len(entries), 0
        for T, c in SEGS[s]:
            d = T - t; t = T
            assert 1 <= d <= 4095
            entries.append((d << 116) | c)
        desc[s] = (first, len(SEGS[s]))
    assert BASE + 2 * len(entries) <= 976
    pw = [0] * 1024
    for e, v in enumerate(entries):
        pw[BASE + 2 * e] = v & ((1 << 64) - 1); pw[BASE + 2 * e + 1] = v >> 64
    dw = [(0x43414c44 << 32) | (BASE << 16) | len(entries)] + [(desc[s][0] << 16) | desc[s][1] for s in range(4)] + [0, 0, 0]
    return pw, dw


def load_events(c0):
    pw, dw = image()
    return [(c0 + a, 0, (a << 64) | pw[a]) for a in range(1024)] + [(c0 + 1024 + a, 1, (a << 64) | dw[a]) for a in range(8)]


def tokpos(u): return 0x1100 + 0x111 * u, 0x200 + 0x10 * u          # each user's own token / position
def run_ev(c, u, stage):
    tok, pos = tokpos(u)
    return (c, 2, (u << 43) | (1 << 42) | (stage << 36) | (tok << 18) | pos)


def schedule(users, s0):
    """(cycle, user, stage): per user token start (stage 0), 3 decode layers one period apart, LM head (stage 37)"""
    out = []
    for u in users:
        sh = SHIFTS[u]
        out.append((s0 + sh, u, 0))
        for p in range(NPER): out.append((s0 + 200 + p * PERIOD + sh, u, p + 1))
        out.append((s0 + 200 + NPER * PERIOD + sh, u, 37))
    return sorted(out)


def build(work, vl, nu, mut, jobs):
    d = work / f'b_nu{nu}_m{mut}'
    exe = d / 'Vtb_mu_ctlm_dv'
    if exe.exists(): return exe
    srcs = [str(ROOT / l.strip()) for l in SRCF.read_text().split('\n') if l.strip()]
    cmd = [vl, '--binary', '--timing', '-O2', '-j', str(jobs), '-Wno-fatal', '-Wno-lint', '-Wno-style', '-Wno-TIMESCALEMOD',
           '-Wno-WIDTHCONCAT', '--x-assign', '0', '--x-initial', '0', '--top-module', 'tb_mu_ctlm_dv',
           f'-GNU={nu}', f'-GMUT={mut}', '-Mdir', str(d)] + srcs + [str(TB)]
    d.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    (d / 'build.log').write_text(r.stdout + r.stderr)
    if r.returncode != 0 or not exe.exists():
        sys.exit(f'BUILD FAILED nu{nu} m{mut}: see {d}/build.log\n' + (r.stdout + r.stderr)[-3000:])
    return exe


def run(work, exe, name, events, ncyc):
    events = sorted(events, key=lambda e: (e[0], e[1]))
    evf, lg = work / f'{name}.ev', work / f'{name}.log'
    evf.write_text(''.join(f'{c} {k} {v:x}\n' for c, k, v in events))
    r = subprocess.run([str(exe), f'+EV={evf}', f'+LOG={lg}', f'+NCYC={ncyc}'], capture_output=True, text=True)
    if r.returncode != 0: sys.exit(f'RUN FAILED {name}: {r.stdout[-2000:]} {r.stderr[-2000:]}')
    out = dict(cmd=[], emb=[], seg=[], mes=[], sua=[], hd=[], cst=[], faults=[], end=None)
    for ln in lg.read_text().split('\n'):
        p = ln.split()
        if not p: continue
        c, k = int(p[0]), p[1]
        if k == 'CMD': out['cmd'].append((c, int(p[2]), int(p[3], 16)))
        elif k == 'EMB': out['emb'].append((c, int(p[2], 16)))
        elif k == 'SEG': out['seg'].append((c, int(p[2], 16), int(p[3], 16), int(p[4], 16)))
        elif k == 'MES': out['mes'].append((c, int(p[2], 16), int(p[3], 16)))
        elif k == 'SUA': out['sua'].append((c, int(p[2])))
        elif k == 'HD': out['hd'].append((c, p[2]))
        elif k == 'CST': out['cst'].append((c, int(p[2])))
        elif k == 'FAULT': out['faults'].append((c, p[2]))
        elif k == 'END': out['end'] = (int(p[2]), p[3], int(p[4]))
    return out


def reloc(c, u):
    """the word user u's playhead issues for image word c (qfd_dv_cmd_cal_mu NU 4, UFOLD 1)"""
    kind, dst = (c >> 1) & 7, (c >> 112) & 15
    if dst == 14: return c
    def put(w, lsb, wid, v):
        assert v < (1 << wid); return (w & ~(((1 << wid) - 1) << lsb)) | (v << lsb)
    def get(w, lsb, wid): return (w >> lsb) & ((1 << wid) - 1)
    ub = u * UVM_STRIDE
    if kind == 4:
        for lsb in (4, 28, 54): c = put(c, lsb, 24, get(c, lsb, 24) + ub)
    elif kind == 2:
        if (c >> 24) & 1: c = put(c, 26, 24, get(c, 26, 24) + ub)
        c = put(c, 51, 2, u)
    elif kind == 1: c = put(c, 4, 9, get(c, 4, 9) + u * PIDX_STRIDE)
    elif kind == 0 and get(c, 4, 2) == 0: c = put(c, 23 + UTAG_LSB, 2, u)
    elif kind == 6: c = put(c, 8, 2, u)
    return c


def expected(sched, C, D):
    """per-user expected CMD words, EMB tokens, SEG (base, tok, pos), MES (tok, pos) at absolute cycles"""
    cmd, emb, seg, mes = [], [], [], []
    for s, u, st in sched:
        tok, pos = tokpos(u)
        if st not in (0, 37) and u == 0: mes.append((s + D, tok, pos))          # D = solo1's measured start -> MES
        for T, c in SEGS[STAGE_SEG(st)]:
            t = s + T + C
            if (c >> 112) & 15 == 14:
                if (c >> 1) & 7 == 1: emb.append((t + 1, tok))
                else: seg.append((t + 1, (c >> 4) & 0xfff, tok, pos))
            else: cmd.append((t, u, reloc(c, u)))
    return sorted(cmd), sorted(emb), sorted(seg), sorted(mes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True); ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--verilator', default=os.environ.get('VERILATOR', 'verilator')); ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    m = a.mut
    e1 = build(work, a.verilator, 1, 0 if m in (16, 17, 18, 19, 20) else m, a.jobs)    # the NU-1 reference stays unmutated
    e4 = build(work, a.verilator, 4, m, a.jobs)
    c0, s0 = 2, 1100
    ld = load_events(c0)
    sch0, sch4 = schedule([0], s0), schedule([0, 1, 2, 3], s0)
    ncyc = s0 + 200 + NPER * PERIOD + SHIFTS[-1] + 600
    res = {'solo1': run(work, e1, 'solo1', ld + [run_ev(*x) for x in sch0], ncyc),
           'solo4': run(work, e4, 'solo4', ld + [run_ev(*x) for x in sch0], ncyc),
           'mu4': run(work, e4, 'mu4', ld + [run_ev(*x) for x in sch4], ncyc)}
    fails = []
    # C1
    for n, r in res.items():
        if r['faults'] or (r['end'] and (r['end'][0] or r['end'][2])): fails.append(f'C1 {n} faulted: {r["faults"]} end {r["end"]}')
    # C2 latency user identity (head side: absolute cycles)
    after = lambda xs: [x for x in xs if x[0] >= s0]
    # the shared hard head runs the fillers' ME segments too (LOCAL SEG), so its outputs are compared up to the first
    # filler LOCAL SEG: that window holds filler token starts and filler decode-stage dh starts (which must not touch it)
    fseg = [x[0] for x in after(res['mu4']['seg']) if x[2] != tokpos(0)[0]]
    hcut = min(fseg) if fseg else 10 ** 9
    u0 = lambda r, cut: dict(cmd=[x for x in after(r['cmd']) if x[1] == 0], hd=[x for x in r['hd'] if x[0] < cut],
                             sua=r['sua'], mes=r['mes'], cst=[x for x in r['cst'] if x[0] < cut])
    for n in ('solo4', 'mu4'):
        a0, b0 = u0(res['solo1'], hcut if n == 'mu4' else 10 ** 9), u0(res[n], hcut if n == 'mu4' else 10 ** 9)
        for k in a0:
            if a0[k] != b0[k]:
                d = [x for x in b0[k] if x not in a0[k]][:2] + [x for x in a0[k] if x not in b0[k]][:2]
                fails.append(f'C2 latency user {k} differs {n} vs solo1 ({len(a0[k])}/{len(b0[k])}; first diffs {str(d)[:300]})')
    # C3 / C4 against the compiled expectation
    cmds = [x for x in res['solo1']['cmd'] if x[0] >= s0]
    C = cmds[0][0] - s0 - SEGS[0][1][0] if cmds else 0
    mes1 = after(res['solo1']['mes'])
    D = mes1[0][0] - (s0 + 200) if mes1 else 0
    if not mes1: fails.append('solo1 has no ME programme start')
    for n, sch in (('solo1', sch0), ('mu4', sch4)):
        w_cmd, w_emb, w_seg, w_mes = expected(sch, C, D)
        g_cmd = sorted((c, u, w) for c, u, w in res[n]['cmd'] if c >= s0)
        for k, got, want in (('C3 cmd words', g_cmd, w_cmd), ('C4 EMB token', after(res[n]['emb']), w_emb),
                             ('C4 SEG base/tok/pos', after(res[n]['seg']), w_seg), ('C4 MES (ME programme start)', after(res[n]['mes']), w_mes)):
            if sorted(got) != want:
                miss = [x for x in want if x not in got][:2]; extra = [x for x in got if x not in want][:2]
                fails.append(f'{n} {k} != compiled (missing {len(set(want) - set(got))} e.g. {str(miss)[:200]}; extra {len(set(got) - set(want))} e.g. {str(extra)[:200]})')
    # C5 head running stage: after every ME start (user 0 dh decode start, or any user's LOCAL SEG), command_stage =
    # the stage of THAT user's running segment, one edge after the start pulse (the leaf latch) -> sampled at MES/SEG + 1
    def stage_at(r, c):
        v = 0
        for cc, s in r['cst']:
            if cc <= c: v = s
        return v
    for n, sch in (('solo1', sch0), ('mu4', sch4)):
        run_stage = lambda u, c: max(((s, st) for s, uu, st in sch if uu == u and s <= c), default=(0, 0))[1]
        bad = []
        for c, base, tok, pos in after(res[n]['seg']):
            u = [uu for uu in range(4) if tokpos(uu)[0] == tok][0]
            if stage_at(res[n], c + 1) != run_stage(u, c): bad.append((c, u, stage_at(res[n], c + 1), run_stage(u, c)))
        for c, tok, pos in after(res[n]['mes']):
            if stage_at(res[n], c + 1) != run_stage(0, c): bad.append((c, 0, stage_at(res[n], c + 1), run_stage(0, c)))
        if bad: fails.append(f'C5 {n} head running stage wrong at {len(bad)} ME starts, e.g. {bad[:3]}')
    g = sorted(x for x in res['mu4']['cmd'] if x[0] >= s0)
    over = {}
    for s, u, st in sch4:
        L = SEGS[STAGE_SEG(st)][-1][0]
        over[(s, u)] = sum(1 for s2, u2, st2 in sch4 if u2 != u and s2 <= s + L and s2 + SEGS[STAGE_SEG(st2)][-1][0] >= s)
    summ = dict(mut=m, verdict='PASS' if not fails else 'FAIL', fails=fails, C_issue_offset=C, D_me_start_offset=D,
                solo1_cmds=len([x for x in res['solo1']['cmd'] if x[0] >= s0]), mu4_cmds=len(g),
                mu4_cmds_per_user={u: sum(1 for x in g if x[1] == u) for u in range(4)},
                mu4_stn_user_fields=sorted({(x[2] >> 51) & 3 for x in g if (x[2] >> 1) & 7 == 2}),
                mu4_amax_user_fields=sorted({(x[2] >> 8) & 3 for x in g if (x[2] >> 1) & 7 == 6}),
                max_other_segments_overlapping=max(over.values()), head_side_changes=len(res['solo1']['hd']),
                head_identity_window=[s0, hcut], mu4_cst_changes=len(res['mu4']['cst']),
                mu4_emb=len(after(res['mu4']['emb'])), mu4_seg=len(after(res['mu4']['seg'])), mu4_mes=len(after(res['mu4']['mes'])),
                end={n: r['end'] for n, r in res.items()})
    (work / f'summary_m{m}.json').write_text(json.dumps(summ, indent=1))
    print(f"MU_CTLM_{summ['verdict']} mut {m}" + ('' if not fails else ': ' + ' | '.join(fails)))
    print(json.dumps({k: v for k, v in summ.items() if k != 'fails'}))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
