#!/usr/bin/env python3
"""MU-S81-2/SEQ (10-19): checker for tb_dsdv_seq_host_mu.sv runs (the real seq_host parent dsdv_seq_host_mux with the
NSLOT 47 host slot table, booted with the compiled L0 programme and the record calendar).

pass mode (exit 0 = PASS):
  check_seq_host_mu.py --dir PROG --plain PLAIN.LOG --single SINGLE.LOG --multi MULTI.LOG --mu MU
  (a) user 0 identical: the multi run's events (VO N/S, CW, SJ, KD, MCe, MRe; edge + payload) before the 2nd start equal
      the single run (mux, user 0 alone) line for line;
  (z) zero added latency: the single mux run vs the plain single-user dsdv_seq_host (same boot, same host stream): same
      KS edge, every VO / CW / SJ / KD event on the same edge with the same payload, except t_kd[31:0] = {user 0, pos 0,
      0} on the mux (0 on the plain unit: the 32 spare bits);
  (b) every start = user 0's events moved by its shift: context beats carry its {user, pos, tok}, its KIT done t_kd =
      {1, tok, user, pos, 0} ON THE KIT DONE EDGE, its windows mu_c = {pos, user, land, ab, 1} / replays mu_rc = {user, 1}
      (replay only where land = 1) with its calendar slot's attributes; exact multiset (nothing missing, nothing extra);
  (c) no fault: issuer fault 0 / jobs = K, t_host[75] = 0, t_mf = 0000.
fault mode (exit 0 = the expected fault was raised):
  check_seq_host_mu.py --multi LOG --fault BIT        t_mf[BIT] rose, on the first fault edge (PROG TMF / MF lines)
Writes <multi log>.json.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / 'tools/s81_dv/layer_prog'))
from check_mu import BODY0, M52, ctx, ctx_templates  # noqa: E402

EV = re.compile(r'^PROG (VO [NS]|CW|SJ|KD|MC\d|MR\d) (\d+) (.*)$', re.M)
KS = re.compile(r'^PROG KS (\d+) user (\d+) pos (\d+) tok (\d+)', re.M)


def attr(s):
    return (1 if s % 3 != 2 else 0, s % 2)


def events(t):
    return [(m.group(1), int(m.group(2)), m.group(3).strip()) for m in EV.finditer(t)]


def mu_lines(f):
    return [tuple(int(x) for x in ln.split()[:5]) for ln in Path(f).read_text().splitlines() if ln.strip()]


def kd_word(tok, user, pos):
    return (1 << 53) | tok << 32 | user << 22 | pos << 1


def move(ev, dt, c0, ck, ctxb, k):
    """user 0's event -> start k's (k = (shift, user, pos, tok, slot)); None = absent for start k"""
    kind, e, p = ev
    _, u, pos, tok, slot = k
    land, ab = attr(slot)
    if kind.startswith('VO'):
        b = int(p, 16)
        b0 = b & ~(M52 << BODY0)
        if b0 in ctxb:
            assert (b >> BODY0) & M52 == c0, 'single run: a context beat without user 0 context'
            b = b0 | ck << BODY0
        p = f'{b:0{len(p)}x}'
    elif kind == 'KD':
        p = f'{kd_word(tok, u, pos):0{len(p)}x}'
    elif kind.startswith('MC'):
        p = f'{(pos << 13 | u << 3 | land << 2 | ab << 1 | 1):0{len(p)}x}'
    elif kind.startswith('MR'):
        if not land:
            return None
        p = f'{(u << 1 | 1):0{len(p)}x}'
    return (kind, e + dt, p)


def tail(t):
    fc = re.search(r'^PROG FCODE (\d+) fault (\d+) jobs (\d+)', t, re.M)
    st = re.search(r'^PROG STATUS \d+ t_host ([0-9a-fA-F]+)', t, re.M)
    mf = re.search(r'^PROG TMF ([01]{4})', t, re.M)
    return fc, st, mf


def check(d, plain, single, multi, mu):
    st, mt, pt = (Path(x).read_text() for x in (single, multi, plain))
    errs = []
    for n, t in (('plain', pt), ('single', st), ('multi', mt)):
        if 'PROG END' not in t:
            errs.append(f'{n} run incomplete (no PROG END)')
    starts = mu_lines(mu)
    s_ks = [int(m.group(1)) for m in KS.finditer(st)]
    p_ks = [int(m.group(1)) for m in KS.finditer(pt)]
    m_ks = [int(m.group(1)) for m in KS.finditer(mt)]
    if errs or len(s_ks) != 1 or len(p_ks) != 1 or len(m_ks) != len(starts):
        return dict(ok=False, errs=errs + [f'KS counts plain {len(p_ks)} single {len(s_ks)} multi {len(m_ks)} '
                                            f'(want 1 / 1 / {len(starts)})'])
    ks0 = s_ks[0]
    for i, k in enumerate(starts):
        if m_ks[i] != ks0 + k[0]:
            errs.append(f'start {i}: KS {m_ks[i]} != {ks0} + {k[0]}')
    se, me, pe = events(st), events(mt), events(pt)
    # (z) mux single vs plain single
    z_ok = p_ks[0] == ks0
    s_core = [x for x in se if not x[0].startswith(('MC', 'MR'))]
    if len(s_core) != len(pe):
        z_ok = False
        errs.append(f'(z) {len(s_core)} unit events on the mux vs {len(pe)} on the plain unit')
    _, u0, p0, t0, _ = starts[0]
    nkd = 0
    for x, y in zip(s_core, pe):
        if x[0] == 'KD' and y[0] == 'KD' and x[1] == y[1]:
            nkd += 1
            xv, yv = int(x[2], 16), int(y[2], 16)
            if yv & 0xFFFFFFFF or xv >> 32 != yv >> 32 or xv & 0xFFFFFFFF != (u0 << 22 | p0 << 1):
                z_ok = False
                errs.append(f'(z) KD edge {x[1]}: mux {x[2]} plain {y[2]} (want plain spare 0, mux spare {{user {u0}, pos {p0}}})')
        elif x != y:
            z_ok = False
            errs.append(f'(z) mux {x} != plain {y}')
            break
    if nkd != 1:
        z_ok = False
        errs.append(f'(z) {nkd} KD events matched (want 1)')
    # (a) user 0 identical
    cut = m_ks[1] if len(m_ks) > 1 else 1 << 62
    a_m = [x for x in me if x[1] < cut]
    a_ok = a_m == se
    if not a_ok:
        n = next((i for i, (x, y) in enumerate(zip(a_m, se)) if x != y), min(len(a_m), len(se)))
        errs.append(f'(a) user 0 differs at event {n}: multi {a_m[n] if n < len(a_m) else None} '
                    f'single {se[n] if n < len(se) else None}')
    # (b) every start = user 0 shifted with its own context / tag / slot attributes
    ctxb = ctx_templates(Path(d))
    c0 = ctx(u0, p0, t0)
    post = [x for x in se if x[1] >= ks0]
    want = Counter(x for x in se if x[1] < ks0)
    for k in starts:
        for x in post:
            y = move(x, k[0], c0, ctx(k[1], k[2], k[3]), ctxb, k)
            if y is not None:
                want[y] += 1
    got = Counter(me)
    miss, extra = want - got, got - want
    if miss:
        errs.append(f'(b) {sum(miss.values())} expected events missing (first {min(miss, key=lambda x: x[1])})')
    if extra:
        errs.append(f'(b) {sum(extra.values())} unexpected events (first {min(extra, key=lambda x: x[1])})')
    kd = [x for x in me if x[0] == 'KD']
    tagged = sum(1 for x in kd if int(x[2], 16) & 0xFFFFFFFF)
    # (c) no fault
    fc, sth, mf = tail(mt)
    if re.search(r'^PROG (FAULT|MF) ', mt, re.M):
        errs.append('(c) fault line in the multi run: ' + re.search(r'^PROG (FAULT|MF) .*$', mt, re.M).group(0))
    if not fc or fc.group(1) != '0' or fc.group(2) != '0' or int(fc.group(3)) != len(starts):
        errs.append(f'(c) issuer final {fc.group(0) if fc else "missing"} (want code 0 fault 0 jobs {len(starts)})')
    if not sth or (int(sth.group(1), 16) >> 75) & 1:
        errs.append('(c) unit status fault t_host[75]')
    if not mf or mf.group(1) != '0000':
        errs.append(f'(c) t_mf {mf.group(1) if mf else "missing"}')
    return dict(ok=not errs, errs=errs, starts=len(starts), users=len({k[1] for k in starts}), ks=m_ks,
                user0_identical=a_ok, zero_latency_vs_plain=z_ok, user0_events=len(se), events_per_start=len(post),
                events_total=len(me), kd_total=len(kd), kd_tagged=tagged, missing=sum(miss.values()),
                extra=sum(extra.values()), max_outstanding=max_out(m_ks, kd))


def max_out(ks, kd):
    ev = [(e, 1) for e in ks] + [(x[1], -1) for x in kd]
    n = m = 0
    for _, d in sorted(ev, key=lambda x: (x[0], x[1])):
        n += d
        m = max(m, n)
    return m


def fault(multi, bit):
    t = Path(multi).read_text()
    _, _, mf = tail(t)
    rose = [(int(e), int(b)) for e, b in re.findall(r'^PROG MF (\d+) bit (\d+)', t, re.M)]
    iss = re.findall(r'^PROG FAULT (\d+) code (\d+)', t, re.M)
    first = [b for e, b in rose if e == rose[0][0]] if rose else []
    # the expected bit must rise FIRST (a later t_mf[2] = the unrecorded start's own return arriving unannounced)
    ok = 'PROG END' in t and mf is not None and mf.group(1)[3 - bit] == '1' and bit in first
    return dict(ok=ok, tmf=mf.group(1) if mf else None, rose=rose, first_bits=first, issuer_faults=iss,
                errs=[] if ok else [f't_mf[{bit}] not raised first (t_mf {mf.group(1) if mf else None}, rose {rose})'])


def main():
    ap = argparse.ArgumentParser()
    for k in ('dir', 'plain', 'single', 'multi', 'mu'):
        ap.add_argument('--' + k)
    ap.add_argument('--fault', type=int)
    a = ap.parse_args()
    r = fault(a.multi, a.fault) if a.fault is not None else check(a.dir, a.plain, a.single, a.multi, a.mu)
    Path(a.multi + '.json').write_text(json.dumps(r, indent=1) + '\n')
    if a.fault is not None:
        print(f"SEQHOST_MU FAULT{a.fault} {'PASS (fault raised)' if r['ok'] else 'FAIL'} t_mf={r['tmf']} "
              f"first={r['rose'][:2]} issuer={r['issuer_faults'][:1]}")
    else:
        print(f"SEQHOST_MU {'PASS' if r['ok'] else 'FAIL'} starts={r.get('starts')} users={r.get('users')} "
              f"user0_identical={r.get('user0_identical')} zero_latency_vs_plain={r.get('zero_latency_vs_plain')} "
              f"kd_tagged={r.get('kd_tagged')}/{r.get('kd_total')} events={r.get('events_total')} "
              f"max_outstanding={r.get('max_outstanding')} {'; '.join(r['errs'][:3])}")
    raise SystemExit(0 if r['ok'] else 1)


if __name__ == '__main__':
    main()
