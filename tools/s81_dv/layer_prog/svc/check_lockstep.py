#!/usr/bin/env python3
"""S81-SVC-5 (11-08) R5 slice-level lock-step checker for tb_svc_lockstep dumps.

usage: check_lockstep.py REPO H16_IMG H16_DUMP H8_IMG H8_DUMP [--out J]   (H8_IMG / H8_DUMP may be a mutant)

Decodes every output stream of the 16 real slices per head / row / dim:
  RT  root score beats (rows 4k..4k+3, H heads a beat; H8: each pass's beats carry its 8 heads) -> score[row][head]
      (+ the PMODE on-die P beats after the (T+3)/4 score beats of each pass are counted, not decoded)
  SE  SE operand rows per slice (16 rows of head = tile)              -> se[slice] ordered rows
  W   SM writes per slice: jid 0x21 = SE e rows (SM), 0x22 = SO o rows -> sm[slice], so[slice] ordered (a, m, d)
  PV  entry P.V words (pv_x[47] = 0) -> pv[head][dim] (value, flag); SO gather words (pv_x[47] = 1) -> gw[head] beats
  JD  jd done / fault pulses, FLT slice fault codes
Checks:
  GOLDEN (each run alone): scores / SE vs sc.hex, P.V vs pv.hex, SO o rows + gather rows vs oexp.hex, exactly one done
         per entry, no fault, all q words sent on time, every stream complete.
  SCHED  (each run alone): entry P.V first / last per pass and jd done vs the compiled cycles in image.json.
  MITER  (H8 vs H16): every per-head / per-slice ordered stream equal (latency shift allowed).
"""
import json
import sys
from pathlib import Path


def load(img):
    img = Path(img)
    rec = json.loads((img / 'image.json').read_text())
    meta = [int(x, 16) for x in (img / 'meta.hex').read_text().split()]
    rd = lambda n: [int(x, 16) for x in (img / n).read_text().split()]
    T = meta[1]
    sc = rd('sc.hex')[:T]
    pv = rd('pv.hex')
    oexp = rd('oexp.hex') if (img / 'oexp.hex').exists() else None
    return rec, meta, sc, pv, oexp


def field(x, lo, n):
    return (x >> lo) & ((1 << n) - 1)


def decode(dump, H, rec, T, tile_of, entry_w=5, entry_e=11):
    passes = rec.get('passes') or [dict(k=0, heads=list(range(16)), pv_first=rec['pv_first'], pv_last=rec['pv_last'])]
    # decode with the CONTRACT (pass k = global heads 8k..8k+7, lower_svc.pass_heads), never with the image's own
    # declaration: a compiler mutant that relabels its passes must not relabel the decode
    passes = [dict(p, heads=list(range(8 * i, 8 * i + 8)) if H == 8 else list(range(16)), declared=p['heads'])
              for i, p in enumerate(passes)]
    LW = H * 132 + 20
    nsb = (T + 3) // 4
    out = dict(score={}, rt_order=[], p_beats=0, se={}, sm={}, so={}, pv={}, pv_order={}, gw={}, jd=[], flt=[],
               pv_cyc={entry_w: [], entry_e: []}, pv_hdr_pass=[], end=None, errors=[])
    rt_k = 0          # root beats seen
    gw_buf = {entry_w: [], entry_e: []}
    aq = {entry_w: 0, entry_e: 0}
    pvc = {}
    for line in Path(dump).read_text().splitlines():
        f = line.split()
        if not f:
            continue
        tag = f[0]
        if tag == 'RT':
            cyc, b = int(f[1]), int(f[2], 16)
            pk, j = divmod(rt_k, 2 * nsb)                 # per pass: nsb score beats then nsb P beats (PMODE)
            rt_k += 1
            if pk >= len(passes):
                out['errors'].append(f'RT beat {rt_k} beyond {len(passes)} passes')
                continue
            if j >= nsb:
                out['p_beats'] += 1
                continue
            r0 = field(b, LW - 16, 16)
            out['rt_order'].append((pk, r0))
            if r0 != 4 * j:
                out['errors'].append(f'RT order pass {pk} beat {j} row {r0}')
            heads = passes[pk]['heads'] if H == 8 else list(range(16))
            for rr in range(4):
                if r0 + rr >= T:
                    continue
                if not field(b, LW - 20 + rr, 1):
                    out['errors'].append(f'RT row {r0 + rr} not held')
                for h, g in enumerate(heads):
                    v = field(b, 4 * H + (rr * H + h) * 32, 32)
                    fl = field(b, rr * H + h, 1)
                    key = (r0 + rr, g)
                    if key in out['score']:
                        out['errors'].append(f'RT score row {r0 + rr} head {g} twice')
                    out['score'][key] = (v, fl)
        elif tag == 'SE':
            s, d = int(f[1]), int(f[3], 16)
            out['se'].setdefault(s, []).append(d)
        elif tag == 'W':
            s, st, a, m, d = int(f[1]), int(f[3], 16), int(f[4], 16), int(f[5], 16), int(f[6], 16)
            jid = st >> 4
            (out['so'] if jid == 0x22 else out['sm']).setdefault(s, []).append((jid, a, m, d))
        elif tag == 'PV':
            s, cyc, x, d = int(f[1]), int(f[2]), int(f[3], 16), int(f[4], 16)
            if s not in (entry_w, entry_e):
                out['errors'].append(f'PV word on non-entry slice {s}')
                continue
            if x >> 47 & 1:
                gw_buf[s].append(d)
                if len(gw_buf[s]) == 3:
                    w0, w1, hd = gw_buf[s]
                    gw_buf[s] = []
                    hh, bt = field(hd, 8, 4), field(hd, 0, 3)
                    rows = [field(w0 if r < 2 else w1, 256 * (r % 2), 256) for r in range(4)]
                    out['gw'].setdefault(hh, []).append((bt, rows, field(hd, 0, 512) >> 12, s))
                continue
            out['pv_cyc'][s].append(cyc)
            n = aq[s]
            aq[s] += 1
            pk, w = divmod(n, 320)
            if pk >= len(passes):
                out['errors'].append(f'PV word {n} at entry {s} beyond the passes')
                continue
            t = (0 if s == entry_e else 8) + w // 40
            wi = w % 5
            if wi == 0:
                if not d >> 512 & 1:
                    out['errors'].append(f'PV header flag missing entry {s} word {n}')
                pvc[s] = (field(d, 64, 8), field(d, 0, 64))
                if H == 8:
                    out['pv_hdr_pass'].append((s, pk, field(d, 32, 1)))
                    if field(d, 32, 1) != pk:
                        out['errors'].append(f'PV header head base bit {field(d, 32, 1)} in pass {pk} at entry {s}')
            else:
                if d >> 512 & 1:
                    out['errors'].append(f'PV data word with header flag entry {s} word {n}')
                c, fl = pvc[s]
                dm = 32 * t + 8 * (wi - 1) + c
                heads = passes[pk]['heads'] if H == 8 else list(range(16))
                for h, g in enumerate(heads):
                    key = (g, dm)
                    if key in out['pv']:
                        out['errors'].append(f'PV head {g} dim {dm} twice')
                    out["pv"][key] = (field(d, 32 * h, 32), field(fl, H * (wi - 1) + h, 1))
                    out['pv_order'].setdefault(g, []).append(dm)
        elif tag == 'JD':
            out['jd'].append((int(f[1]), int(f[2]), int(f[3])))
        elif tag == 'FLT':
            out['flt'].append((int(f[1]), int(f[2]), f[3]))
        elif tag == 'END':
            out['end'] = line
    out['aq'] = aq
    out['passes'] = passes
    return out


def golden(o, rec, meta, sc, pv, oexp, T, tile_of, entry_w=5, entry_e=11):
    bad = list(o['errors'])
    nsc = 0
    for r in range(T):
        for g in range(16):
            e = sc[r] >> (33 * g)
            got = o['score'].get((r, g))
            nsc += got is not None
            if got != (e & 0xFFFFFFFF, e >> 32 & 1):
                bad.append(f'SC row {r} head {g} got {got} exp {e & 0xFFFFFFFF:08x}/{e >> 32 & 1}')
    for s in range(16):
        t = tile_of(s)
        rows = o['se'].get(s, [])
        if len(rows) != (T + 15) // 16:
            bad.append(f'SE slice {s}: {len(rows)} rows, exp {(T + 15) // 16}')
        for n, d in enumerate(rows):
            for rr in range(16):
                r = 16 * n + rr
                if r < T and field(d, 32 * rr, 32) != (sc[r] >> (33 * t)) & 0xFFFFFFFF:
                    bad.append(f'SE slice {s} row {r}')
        if len(o['sm'].get(s, [])) != len(rows):
            bad.append(f'SM slice {s}: {len(o["sm"].get(s, []))} e-row writes vs {len(rows)} SE rows')
    npv = 0
    for g in range(16):
        for dm in range(512):
            e = pv[dm] >> (33 * g)
            got = o['pv'].get((g, dm))
            npv += got is not None
            if got != (e & 0xFFFFFFFF, e >> 32 & 1):
                bad.append(f'PV head {g} dim {dm} got {got} exp {e & 0xFFFFFFFF:08x}/{e >> 32 & 1}')
    if oexp is not None:
        for s in range(16):
            g = tile_of(s)
            ws = o['so'].get(s, [])
            if len(ws) != 32:
                bad.append(f'SO slice {s}: {len(ws)} o rows, exp 32')
            for k, (jid, a, m, d) in enumerate(ws[:32]):
                half = field(d, 256, 256) if g % 2 else field(d, 0, 256)
                if a != (0x200 + 8 * k + g // 2) or m != (0xff00 if g % 2 else 0x00ff) or half != oexp[32 * g + k]:
                    bad.append(f'SO slice {s} head {g} row {k} a {a:x} m {m:x}')
        for g in range(16):
            bs = o['gw'].get(g, [])
            if [b for b, *_ in bs] != list(range(8)):
                bad.append(f'GW head {g} beats {[b for b, *_ in bs]}')
            for bt, rows, _, s in bs:
                if (s == entry_w) != (g >= 8):
                    bad.append(f'GW head {g} at entry {s}')
                for r in range(4):
                    if 4 * bt + r < 32 and rows[r] != oexp[32 * g + 4 * bt + r]:
                        bad.append(f'GW head {g} beat {bt} row {r}')
    done = [(k, c) for k, c, v in o['jd'] if v & 1]
    fault = [(k, c, v) for k, c, v in o['jd'] if v & 2]
    if sorted(k for k, _ in done) != [0, 1]:
        bad.append(f'jd done pulses {done} (exp one per entry)')
    if fault:
        bad.append(f'jd fault {fault}')
    if o['flt']:
        bad.append(f'slice faults {o["flt"][:6]}')
    if o['end'] is None:
        bad.append('no END line (bench did not finish)')
    else:
        e = o['end'].split()
        if int(e[e.index('late') + 1]) or e[e.index('qi') + 1] != e[e.index('nq') + 1] or e[e.index('slice_faults') + 1] != '0000':
            bad.append(f'END {o["end"]}')
    return bad, dict(scores=nsc, pv=npv)


def sched(o, rec, entry_w=5, entry_e=11):
    """compiled vs measured entry P.V windows and jd done (the H8 latencies are PLACEHOLDERS until calibrated)"""
    rows = []
    for s in (entry_w, entry_e):
        cy = o['pv_cyc'][s]
        for p in o['passes']:
            k = p['k']
            seg = cy[320 * k:320 * (k + 1)]
            rows.append(dict(entry=s, k=k, exp=[p['pv_first'], p['pv_last']], got=[seg[0], seg[-1]] if seg else None,
                             back_to_back=bool(seg) and seg[-1] - seg[0] == len(seg) - 1, words=len(seg)))
    done = {k: c for k, c, v in o['jd'] if v & 1}
    rows.append(dict(done_w=[rec['done_w'], done.get(0)], done_e=[rec['done_e'], done.get(1)]))
    ok = all(r.get('got') == r.get('exp') and r.get('back_to_back') for r in rows[:-1]) and \
        rows[-1]['done_w'][0] == rows[-1]['done_w'][1] and rows[-1]['done_e'][0] == rows[-1]['done_e'][1]
    return ok, rows


def miter(a, b):
    """a = H16 run, b = H8 run: equal per-head / per-slice ordered streams"""
    bad = []
    if a['score'] != b['score']:
        ks = sorted(set(a['score']) | set(b['score']))
        d = [k for k in ks if a['score'].get(k) != b['score'].get(k)]
        bad.append(f'scores differ at {len(d)} (row, head), first {d[:4]}')
    for nm in ('se', 'sm', 'so'):
        for s in range(16):
            if a[nm].get(s, []) != b[nm].get(s, []):
                bad.append(f'{nm} slice {s} stream differs ({len(a[nm].get(s, []))} vs {len(b[nm].get(s, []))} items)')
    if a['pv'] != b['pv']:
        ks = sorted(set(a['pv']) | set(b['pv']))
        d = [k for k in ks if a['pv'].get(k) != b['pv'].get(k)]
        bad.append(f'P.V differs at {len(d)} (head, dim), first {d[:4]}')
    for g in range(16):
        if a['pv_order'].get(g) != b['pv_order'].get(g):
            bad.append(f'P.V dim order of head {g} differs')
        ga = [(bt, rows) for bt, rows, _, _ in a['gw'].get(g, [])]
        gb = [(bt, rows) for bt, rows, _, _ in b['gw'].get(g, [])]
        if ga != gb:
            bad.append(f'SO gather stream of head {g} differs')
    return bad


def main():
    repo, i16, d16, i8, d8 = sys.argv[1:6]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    sys.path.insert(0, str(Path(repo) / 'tools/s81_dv/layer_prog'))
    import lower_svc as L
    res = {}
    dec = {}
    for name, img, dump, H in (('h16', i16, d16, 16), ('h8', i8, d8, 8)):
        rec, meta, sc, pv, oexp = load(img)
        T = meta[1]
        o = decode(dump, H, rec, T, L.tile_of)
        g, cnt = golden(o, rec, meta, sc, pv, oexp, T, L.tile_of)
        sok, srows = sched(o, rec)
        dec[name] = o
        res[name] = dict(img=str(img), dump=str(dump), golden='PASS' if not g else 'FAIL', golden_errors=len(g),
                         first_errors=g[:12], counts=cnt, rt_score_beats=len(o['rt_order']), p_beats=o['p_beats'],
                         pv_words=o['aq'], gw_heads=len(o['gw']), so_rows=sum(len(v) for v in o['so'].values()),
                         sched='PASS' if sok else 'FAIL', sched_rows=srows, pv_hdr_pass=sorted(set(o['pv_hdr_pass'])),
                         end=o['end'])
    m = miter(dec['h16'], dec['h8'])
    res['miter'] = dict(verdict='EQUAL' if not m else 'DIFFER', differences=m[:20], n=len(m))
    res['verdict'] = 'PASS' if (res['h16']['golden'] == 'PASS' and res['h8']['golden'] == 'PASS' and not m) else 'FAIL'
    txt = json.dumps(res, indent=1)
    if out:
        Path(out).write_text(txt + '\n')
    print(txt)


if __name__ == '__main__':
    main()
