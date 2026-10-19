#!/usr/bin/env python3
"""MU-KV-CTX bench (2026-10-19, coordinator 0kg): the fillers' initial context from the KV die host plane over the EXISTING
KV->compute d2d record stream into the compute ctlm boot-context loader (qfd_tt_ctlm_dv OPSEG, main 811e75a88).

    mu_kvctx_bench.py --work DIR [--kmut M] [--rmut M] [--verilator PATH] [--jobs N]

Harness tb_mu_kvctx.sv (see its header).  The ctlm half is the MU-QW-B1 op-segment bench (rtl/test/mu_qwen_seq/
mu_opseg_bench.py, imported unchanged): case `red` (mu_opcal F = 16, 2 layers, 3 frames + 2,000 edges), its checks C1..C7
(C2 = the latency user cycle-identical to the NU 1 reference, C5 = every filler EMB / SEG uses the filler's bank, which
starts from its initial context PRE[u]) -- except that the compute image's DW5 / DW6 carry NO context record here: the
records come from the KV die only.  KV-side schedule (cycles before the first L0 start S0 = 1100):
  user 0 request at 51 (U0), fillers 1 / 2 / 3 admitted at 61 / 71 / 81 (PRE[u]); filler 1 continues at 301 (pos + 1, not
  an admission); filler 3 continues at 351 BEFORE its initial context is sent (the initial context must survive); user 0's
  next step at 501; slot pairs at 200 / 400 / 600 / 800 (rotation 1, 2, 3, then none: the user-0 copy).
Checks (PASS needs all, plus mu_opseg_bench C1..C7):
  K1 KV identity: on every edge the reference port (MU 0 original, user-0 traffic, single-slot calendar) sends a word, the
     MU port sends the SAME word (valid, observed, 548 bits) -- 4 edges;
  K2 the MU port sends 8 words (4 pairs), all observed;
  K3 the face's own kind-12 receiver: no fault, and after the 2nd slot of every pair its TAG is user 0's current TAG;
  K4 the leaf loads exactly users 1, 2, 3 in that order with PRE[u] (token, {5'd0, position}), before the first filler
     EMB / SEG; no other load;
  K5 no sticky fault on the KV MU port, the reference port, the face receiver or the leaf.
Mutants (each must FAIL): --kmut 1 wrong user field, --kmut 2 wrong slot (pair order swapped), --kmut 3 producer off;
--rmut 1 leaf loads into the wrong user.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'rtl/test/mu_qwen_seq'))
import mu_opseg_bench as B                                # noqa: E402
O = B.O

TB = HERE / 'tb_mu_kvctx.sv'
LIST = HERE / 'lists/tb_mu_kvctx.f'
NU, LINK = B.NU, 14            # send -> compute RX slot = 2 record-port edges + LINK = 16 = the production image (K cyc 2 -> C arrive 18)
PRE, U0 = B.PRE, B.U0


def ep(u, seq): return (seq << 2) | u
def tag(e, tok, pos): return (e << 43) | (tok << 19) | (pos << 6)


U0B = ((U0[0] + 7) & 0x3FFFF, U0[1] + 1)          # user 0's next step
SCHED = [  # (cycle of the request; the epoch pulse is one edge before), user, seq, token, position
    (51, 0, 1) + U0, (61, 1, 1) + PRE[1], (71, 2, 1) + PRE[2], (81, 3, 1) + PRE[3],
    (301, 1, 2, (PRE[1][0] + 5) & 0x3FFFF, PRE[1][1] + 1), (351, 3, 2, (PRE[3][0] + 9) & 0x3FFFF, PRE[3][1] + 1),
    (501, 0, 2) + U0B]
PAIRS = [200, 400, 600, 800]


def kv_events():
    ev = []
    for c, u, s, tok, pos in SCHED:
        e = ep(u, s)
        ev.append((c - 1, 4, e))
        ev.append((c, 5, (s & 3) << 59 | tag(e, tok, pos)))
    ev += [(c, 6, 0) for c in PAIRS]
    return ev


_orig_events_for = B.events_for


def events_for(pb, face, res, users, ctx=True):
    if users == {0}:
        return _orig_events_for(pb, face, res, users, ctx=False)
    return _orig_events_for(pb, face, res, users, ctx=False) + kv_events()   # NO image context: the KV die sends it


B.events_for = events_for


def build(work, vl, kmut, rmut, jobs):
    d = work / f'b_kvctx_k{kmut}_r{rmut}'
    exe = d / 'Vtb_mu_kvctx'
    if exe.exists(): return exe
    srcs = [str(ROOT / l.strip()) for l in LIST.read_text().split('\n') if l.strip() and not l.startswith('#')]
    cmd = [vl, '--binary', '--timing', '-O2', '-j', str(jobs), '-Wno-fatal', '-Wno-lint', '-Wno-style', '-Wno-TIMESCALEMOD',
           '-Wno-WIDTHCONCAT', '--x-assign', '0', '--x-initial', '0', '--top-module', 'tb_mu_kvctx',
           f'-GNU={NU}', '-GMUT=0', '-GOPSEG=1', f'-GKMUT={kmut}', f'-GRMUT={rmut}', f'-GLINK={LINK}', '-Mdir', str(d)] + srcs
    d.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    (d / 'build.log').write_text(r.stdout + r.stderr)
    if r.returncode != 0 or not exe.exists():
        sys.exit(f'BUILD FAILED kvctx k{kmut} r{rmut}: see {d}/build.log\n' + (r.stdout + r.stderr)[-3000:])
    return exe


def kv_checks(log, mu, fails, summ):
    ktx, kid, frx, ld, kend, kidn = [], [], [], [], None, None
    for ln in log.read_text().split('\n'):
        p = ln.split()
        if len(p) < 2: continue
        c, k = int(p[0]), p[1]
        if k == 'KTX': ktx.append((c, int(p[2]), int(p[3], 16)))
        elif k == 'KID': kid.append(ln)
        elif k == 'KIDN': kidn = int(p[2])
        elif k == 'FRX': frx.append((c, int(p[2], 16), int(p[3]), int(p[4])))
        elif k == 'CTXLD': ld.append((c, int(p[2]), int(p[3], 16), int(p[4], 16)))
        elif k == 'KEND': kend = tuple(int(x) for x in p[2:6])
    # K1
    if kid or kidn != len(PAIRS):
        fails.append(f'K1 KV identity: {len(kid)} reference words differ (of {kidn}, want {len(PAIRS)}): {kid[:2]}')
    # K2
    if len(ktx) != 2 * len(PAIRS) or any(o != 1 for c, o, t in ktx):
        fails.append(f'K2 MU port words {len(ktx)} (want {2 * len(PAIRS)}), unobserved {[x for x in ktx if x[1] != 1][:2]}')
    # K3 face: the 2nd received slot of every pair ends on user 0's current TAG
    u0tags = [(c, tag(ep(0, s), tok, pos)) for c, u, s, tok, pos in SCHED if u == 0]
    bad3 = []
    if len(frx) != 2 * len(PAIRS): bad3.append(f'{len(frx)} face receives (want {2 * len(PAIRS)})')
    for i in range(1, len(frx), 2):
        c, t, v, f = frx[i]
        want = [x for cc, x in u0tags if cc < c][-1]
        if t != want or not v: bad3.append(f'pair end {c}: face TAG {t:x} (want user 0 {want:x}) valid {v}')
    if any(f for c, t, v, f in frx): bad3.append('face receiver fault')
    if bad3: fails.append('K3 face ' + '; '.join(bad3[:3]))
    # K4 leaf loads
    want4 = [(u, PRE[u][0], PRE[u][1]) for u in (1, 2, 3)]
    got4 = [(u, tk, ps) for c, u, tk, ps in ld]
    fill = [x[0] for x in mu['emb'] + mu['seg'] if x[1] != 0]
    late = [c for c, u, tk, ps in ld if fill and c >= min(fill)]
    if got4 != want4 or late:
        fails.append(f'K4 leaf loads {got4} (want {want4}); after the first filler EMB/SEG: {late[:2]}')
    # K5
    if kend != (0, 0, 0, 0):
        fails.append(f'K5 sticky faults kv_mu / kv_ref / face / leaf = {kend}')
    summ['kv'] = dict(ktx=len(ktx), kid_compared=kidn, kid_bad=len(kid), face_rx=[(c, f'{t:x}') for c, t, v, f in frx],
                      loads=ld, kend=kend, link=LINK, pairs=PAIRS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True); ap.add_argument('--kmut', type=int, default=0)
    ap.add_argument('--rmut', type=int, default=0)
    ap.add_argument('--verilator', default=os.environ.get('VERILATOR', 'verilator')); ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    e1 = B.build(work, a.verilator, 1, 0, 0, a.jobs)
    e4 = build(work, a.verilator, a.kmut, a.rmut, a.jobs)
    fails, summ = [], dict(kmut=a.kmut, rmut=a.rmut)
    cal = O.compile_frame(16, layers=2)
    rd = work / 'rom_red'; rd.mkdir(exist_ok=True)
    (rd / f'{B.INST}.viamap.hex').write_text(O.viamap_hex(O.rom_words(cal)))
    name = f'kvctx_k{a.kmut}_r{a.rmut}'
    B.check_case(name, cal, B.RED_FRAMES + 1, B.S0 + B.RED_FRAMES * cal['H'] + 2000, e1, e4, work, rd, 0, fails, summ)
    # re-read the MU run's log (check_case ran it as <name>_mu)
    log = work / f'{name}_mu.log'
    mu_parsed = dict(emb=[], seg=[])
    for ln in log.read_text().split('\n'):
        p = ln.split()
        if len(p) > 2 and p[1] == 'EMB': mu_parsed['emb'].append((int(p[0]), int(p[2])))
        if len(p) > 2 and p[1] == 'SEG': mu_parsed['seg'].append((int(p[0]), int(p[2])))
    kv_checks(log, mu_parsed, fails, summ)
    summ['verdict'] = 'PASS' if not fails else 'FAIL'
    summ['fails'] = fails
    (work / f'summary_{name}.json').write_text(json.dumps(summ, indent=1, default=str))
    print(f"MU_KVCTX_{summ['verdict']} kmut {a.kmut} rmut {a.rmut}" + ('' if not fails else ': ' + ' | '.join(fails)))
    print(json.dumps({k: v for k, v in summ.items() if k != 'fails'}, default=str)[:4000])
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
