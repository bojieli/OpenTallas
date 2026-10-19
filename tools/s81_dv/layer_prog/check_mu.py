#!/usr/bin/env python3
"""MU-S81/TOK (10-19): check a multi-user run of the real dsdv_seq_host (tb_dv_prog_seqhost.sv +mu=FILE) against the
single-user run of the same programme (the same TB, +mu with user 0's line only).

PASS =
  (a) user 0 identical: every event line (VO N/S, CW, SJ, KD with its edge and payload) of the multi run before user 1's
      KS edge equals the single run's event lines, line for line (boot + user 0's whole programme);
  (b) shift: the multi run's KS edges are KS_0 + shift_k, and its event multiset after boot is exactly the union over
      users k of the single run's post-KS events moved by shift_k, with user k's own context: a V beat that carries the
      context (seq_host context 1, body[159:108] = {user 10, pos 21, tok 21}) carries user k's, the KIT done carries
      user k's tok; no event missing, none extra;
  (c) no fault: issuer fault 0 / code 0, unit status t_host[75] = 0, jobs accepted = K.
Writes mu_check.json next to the multi log.
    check_mu.py --dir PROGDIR --single SINGLE.LOG --multi MULTI.LOG --mu MU.TXT        exit 0 = PASS
    check_mu.py --make PROGDIR/prog/mu_slots.json --copy A --out MU.TXT [--first N] [--pass P]
        the job starts of one die (the users of that group copy, dv_layer_compile --mu-cal): "shift user pos tok" a line,
        shift = start - the copy's first start (multiples of 4 on a --phase-q 4 calendar), pos = pos0 + P * stride,
        tok = 1000 + 7 * user (bench token ids: data only)
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

BODY0 = 21 + 26 + 108          # beat bit of payload body[108] (beat[21 +: 186] = payload, body = payload[26 +: 160])
M52 = (1 << 52) - 1
EV = re.compile(r'^PROG (VO [NS]|CW|SJ|KD) (\d+) (.*)$', re.M)


def events(txt):
    return [(m.group(1), int(m.group(2)), m.group(3).strip()) for m in EV.finditer(txt)]


def ctx(user, pos, tok):
    return (user << 42) | (pos << 21) | tok


def ctx_templates(d):
    """beats (context bits 0) of the templates used by a context-1 V row"""
    cal = json.loads((d / 'prog/calendar.json').read_text())
    tm = json.loads((d / 'prog/ctl_templates.json').read_text())
    T = [int(t['payload186'], 16) for t in tm['templates']]
    out = set()
    for r in cal['rows']:
        if r['engine'] in (0, 1) and (r['arg'] >> 7) & 3 == 1:
            out.add(1 | 4 << 9 | T[r['arg'] & 0x7F] << 21)
    return out


def move(ev, dt, c0, ck, ctxb, tok_k):
    k, e, p = ev
    if k.startswith('VO'):
        b = int(p, 16)
        b0 = b & ~(M52 << BODY0)
        if b0 in ctxb:
            assert (b >> BODY0) & M52 == c0, 'single run: a context beat without user 0 context'
            b = b0 | ck << BODY0
        p = f'{b:0{len(p)}x}'
    elif k == 'KD':
        v = int(p, 16)
        v = (v & ~(((1 << 21) - 1) << 32)) | tok_k << 32
        p = f'{v:0{len(p)}x}'
    return (k, e + dt, p)


def check(d, single, multi, mu):
    users = [tuple(int(x) for x in ln.split()) for ln in Path(mu).read_text().splitlines() if ln.strip()]
    st, mt = Path(single).read_text(), Path(multi).read_text()
    errs = []
    s_ks = [int(x) for x in re.findall(r'^PROG KS (\d+)', st, re.M)]
    m_ks = [int(x) for x in re.findall(r'^PROG KS (\d+)', mt, re.M)]
    for name, t in (('single', st), ('multi', mt)):
        if 'PROG END' not in t:
            errs.append(f'{name} run incomplete (no PROG END)')
    if len(s_ks) != 1:
        errs.append(f'single run: {len(s_ks)} KS')
    if len(m_ks) != len(users):
        errs.append(f'multi run: {len(m_ks)} KS for {len(users)} users')
    if errs:
        return dict(ok=False, errs=errs)
    ks0 = s_ks[0]
    for k, (sh, *_r) in enumerate(users):
        if m_ks[k] != ks0 + sh:
            errs.append(f'user {k}: KS {m_ks[k]} != {ks0} + shift {sh}')
    se, me = events(st), events(mt)
    # (a) user 0 == single-user run, line for line
    cut = m_ks[1] if len(m_ks) > 1 else 1 << 62
    a_m = [x for x in me if x[1] < cut]
    a_ok = a_m == se
    if not a_ok:
        n = next((i for i, (x, y) in enumerate(zip(a_m, se)) if x != y), min(len(a_m), len(se)))
        errs.append(f'(a) user 0 differs from the single-user run at event {n} '
                    f'(multi {a_m[n] if n < len(a_m) else None} vs single {se[n] if n < len(se) else None})')
    # (b) every user = user 0 shifted by its shift with its own context
    ctxb = ctx_templates(Path(d))
    _, u0, p0, t0 = users[0]
    c0 = ctx(u0, p0, t0)
    post = [x for x in se if x[1] >= ks0]
    boot = [x for x in se if x[1] < ks0]
    want = Counter(boot)
    n_ctx = sum(1 for x in post if x[0].startswith('VO') and (int(x[2], 16) & ~(M52 << BODY0)) in ctxb)
    for k, (sh, u, p, t) in enumerate(users):
        for x in post:
            want[move(x, sh, c0, ctx(u, p, t), ctxb, t)] += 1
    got = Counter(me)
    miss, extra = want - got, got - want
    if miss:
        errs.append(f'(b) {sum(miss.values())} expected events missing (first {min(miss, key=lambda x: x[1])})')
    if extra:
        errs.append(f'(b) {sum(extra.values())} unexpected events (first {min(extra, key=lambda x: x[1])})')
    # (c) no fault
    fl = re.findall(r'^PROG FAULT (\d+) code (\d+)', mt, re.M)
    fc = re.search(r'^PROG FCODE (\d+) fault (\d+) jobs (\d+)', mt, re.M)
    sth = re.search(r'^PROG STATUS \d+ t_host ([0-9a-fA-F]+)', mt, re.M)
    if fl:
        errs.append(f'(c) issuer fault at edge {fl[0][0]} code {fl[0][1]}')
    if not fc or fc.group(1) != '0' or fc.group(2) != '0' or int(fc.group(3)) != len(users):
        errs.append(f'(c) final issuer state {fc.group(0) if fc else "missing"} (want code 0 fault 0 jobs {len(users)})')
    if not sth or (int(sth.group(1), 16) >> 75) & 1:
        errs.append('(c) unit status fault t_host[75] = 1')
    return dict(ok=not errs, errs=errs, users=len(users), shifts=[u[0] for u in users], ks=m_ks,
                user0_identical=a_ok, user0_events=len(se), events_per_user=len(post), ctx_beats_per_user=n_ctx,
                events_total=len(me), missing=sum(miss.values()), extra=sum(extra.values()),
                faults=[dict(edge=int(e), code=int(c)) for e, c in fl])


def make(slots, copy, out, first=None, pas=3):
    t = json.loads(Path(slots).read_text())
    rows = sorted((r for r in t['rows'] if r['copy'] == copy), key=lambda r: r['start'])[:first]
    s0 = rows[0]['start']
    ln = [f"{r['start'] - s0} {r['user']} {r['pos0'] + pas * r['stride']} {1000 + 7 * r['user']}" for r in rows]
    Path(out).write_text('\n'.join(ln) + '\n')
    return len(ln)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir')
    ap.add_argument('--single')
    ap.add_argument('--multi')
    ap.add_argument('--mu')
    ap.add_argument('--make')
    ap.add_argument('--copy', default='A')
    ap.add_argument('--out')
    ap.add_argument('--first', type=int)
    ap.add_argument('--pass', dest='pas', type=int, default=3)
    a = ap.parse_args()
    if a.make:
        print(make(a.make, a.copy, a.out, a.first, a.pas))
        return
    r = check(a.dir, a.single, a.multi, a.mu)
    (Path(a.multi).parent / 'mu_check.json').write_text(json.dumps(r, indent=1) + '\n')
    print(f"SEQHOST_MU {'PASS' if r['ok'] else 'FAIL'} users={r.get('users')} user0_identical={r.get('user0_identical')} "
          f"events={r.get('events_total')} ctx_beats/user={r.get('ctx_beats_per_user')} {'; '.join(r['errs'][:4])}")
    raise SystemExit(0 if r['ok'] else 1)


if __name__ == '__main__':
    main()
