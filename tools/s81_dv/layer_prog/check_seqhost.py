#!/usr/bin/env python3
"""LAYERBENCH-S81: check the real dsdv_seq_host run of a compiled layer programme (tb_dv_prog_seqhost.sv log) against the
compiled calendar (dv_layer_compile.py prog/calendar.json + ctl_templates.json).

PASS = every V command row (engine 0 / 1) left as exactly one beat on vo_n / vo_s, on edge  KS + issue + C  with ONE
constant C for all rows (the static schedule: no row moved relative to another), beat = {[0] 1, kind 0, hops 0, src 4,
payload = the row's template}; the KIT done left t_kd; no other beat; unit status fault bit t_host[75] = 0.
Also writes check.json (C, per-row edges).
    check_seqhost.py --dir PROGDIR --log RUN.LOG [--expect-c N]       exit 0 = PASS
    make-mutant: check_seqhost.py --mutant shift:K --dir PROGDIR --out MUTDIR   (row K issue / done + 1: must FAIL)
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dv_layer_compile as C  # noqa: E402


def bits(v, hi, lo):
    return (v >> lo) & ((1 << (hi - lo + 1)) - 1)


def check(d, log, expect_c=None):
    cal = json.loads((d / 'prog/calendar.json').read_text())
    tm = json.loads((d / 'prog/ctl_templates.json').read_text())
    T = [int(t['payload186'], 16) for t in tm['templates']]
    txt = Path(log).read_text()
    ks = [int(x) for x in re.findall(r'^PROG KS (\d+)', txt, re.M)]
    vo = [(m.group(1), int(m.group(2)), int(m.group(3), 16)) for m in re.finditer(r'^PROG VO ([NS]) (\d+) ([0-9a-fA-F]+)', txt, re.M)]
    kd = [int(m.group(1)) for m in re.finditer(r'^PROG KD (\d+)', txt, re.M)]
    st = re.search(r'^PROG STATUS \d+ t_host ([0-9a-fA-F]+)', txt, re.M)
    errs = []
    if len(ks) != 1 or not st or 'PROG END' not in txt:
        return dict(ok=False, errs=['run incomplete (KS / STATUS / END missing)'])
    t_host = int(st.group(1), 16)
    if bits(t_host, 75, 75):
        errs.append(f'unit fault t_host[75] = 1 (status {bits(t_host, 75, 65):011b})')
    rows = [r for r in cal['rows'] if r['engine'] in (0, 1)]
    used = set()
    offs = []
    per = []
    for r in rows:
        side = 'N' if r['engine'] == 0 else 'S'
        want = 1 | 4 << 9 | T[r['arg'] & 0x7F] << 21
        hit = [i for i, (s, e, b) in enumerate(vo) if s == side and b == want and i not in used]
        if not hit:
            errs.append(f"row {r['i']} ({r['what']}): no matching beat on vo_{side.lower()}")
            continue
        # the earliest unused matching beat
        i = min(hit, key=lambda i: vo[i][1])
        used.add(i)
        off = vo[i][1] - (ks[0] + r['issue'])
        offs.append(off)
        per.append(dict(row=r['i'], what=r['what'], issue=r['issue'], edge=vo[i][1], offset=off))
    extra = [vo[i] for i in range(len(vo)) if i not in used]
    if extra:
        errs.append(f'{len(extra)} unexpected V beats (first at edge {extra[0][1]})')
    cset = sorted(set(offs))
    if len(cset) > 1:
        errs.append(f'command offsets differ: {cset} (a row moved off the static schedule)')
    if expect_c is not None and cset and cset != [expect_c]:
        errs.append(f'offset {cset} != expected {expect_c}')
    kit = [r for r in cal['rows'] if r['engine'] == 14]
    if kit and not kd:
        errs.append('KIT row issued but no t_kd done')
    res = dict(ok=not errs, errs=errs, C=cset[0] if len(cset) == 1 else cset, ks=ks[0], rows=per,
               kit_edge=kd[0] if kd else None, kit_offset=(kd[0] - ks[0] - kit[0]['issue']) if kd and kit else None,
               t_host_status=f'{bits(t_host, 75, 65):011b}')
    return res


def mutant(d, spec, out):
    kind, k = spec.split(':')
    assert kind == 'shift'
    k = int(k)
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(d, out)
    cal = json.loads((d / 'prog/calendar.json').read_text())
    tm = json.loads((d / 'prog/ctl_templates.json').read_text())
    rows = cal['rows']
    r = rows[k]
    assert r['engine'] in (0, 1), 'mutate a V row'
    r = dict(r, issue=r['issue'] + 1, done=r['done'] + 1)
    rows = rows[:k] + [r] + rows[k + 1:]
    T = [int(t['payload186'], 16) for t in tm['templates']]
    hs = [C.csr_len(len(rows)), C.csr_pw(0, C.pw_header(len(rows)))]
    for i, x in enumerate(rows):
        hs += [C.csr_pw(a, dd) for a, dd in C.pw_row_words(i, C.pack_row(x['done'], x['issue'], x['engine'], x['arg']))]
    hs.append(C.csr_pw(0, C.pw_header(len(rows), seal=True)))
    hs += [C.csr_template(i, p) for i, p in enumerate(T)]
    (out / 'prog/host_boot.memh').write_text(C.memh(hs, 515))   # calendar.json stays the ORIGINAL (the check's reference)
    return len(hs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--log')
    ap.add_argument('--expect-c', type=int)
    ap.add_argument('--mutant')
    ap.add_argument('--out')
    a = ap.parse_args()
    d = Path(a.dir)
    if a.mutant:
        print(mutant(d, a.mutant, a.out))
        return
    r = check(d, a.log, a.expect_c)
    (Path(a.log).parent / 'check.json').write_text(json.dumps(r, indent=1) + '\n')
    print(f"SEQHOST_PROG {'PASS' if r['ok'] else 'FAIL'} C={r.get('C')} kit_offset={r.get('kit_offset')} "
          f"rows={len(r.get('rows', []))} status={r.get('t_host_status')} {'; '.join(r['errs'][:4])}")
    sys.exit(0 if r['ok'] else 1)


if __name__ == '__main__':
    main()
