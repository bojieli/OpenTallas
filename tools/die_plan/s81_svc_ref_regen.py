#!/usr/bin/env python3
"""Regenerate the svc memory-closure reference from the current T7 bound (DIE-S81-56/PLAN 11-05, S81-066).

The class transforms name T7 nets of the 61c902f1 bound.  Bind numbers and src_<hash> names move when a source file
moves (1ec013265f added one line and lowered two `inside` predicates in dsdv_svc_att.sv, so src_ hashes and plain N_Y
numbers changed; the logic the transforms touch did not).  This tool pairs the nets of the 61c902f1 bound and a current
T7 bound, writes the current bound as the new reference and the token map for the transforms, and proves the pairing:

  (a) residual: the 61c902f1 bound renamed by the map compared with the current bound, comments off, as line multisets.
      What remains must be the source change only; no net the transforms name may appear in it.
  (b) closure: the ported chain on the current T7 (reference + map) leaves exactly the same residual against the
      renamed 12605dc2 closure, and 12605dc2 itself is reproduced byte-exactly from 61c902f1.

usage: s81_svc_ref_regen.py CURRENT_T7_BOUND OUT_DIR [--old-line-shift FILE:FROM:DELTA ...]
"""
import argparse, collections, difflib, gzip, hashlib, json, re, sys, threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.setrecursionlimit(1000000)
import s81_svc_memory_closure as CL

P = 'w_u_rsv_14_u_u_att_'; E = P + 'u_eng_'; TOP = 'w_u_rsv_14_u_'
ID = re.compile(r'\b(?:[wg]_u_rsv_14_\w+|ot_bind_native_[0-9a-f]+)\b')
HASHED = re.compile(r'src_[0-9a-f]{20}|_\d+_Y$|driver_\d+_')


def h(*a): return hashlib.sha1(repr(a).encode()).hexdigest()[:16]


def nid(t):
    if t.startswith('ot_bind'): return 'NAT'
    return re.sub(r'(?<=_)\d+(?=_|$)', 'N', re.sub(r'src_[0-9a-f]{20}', 'src_H', t))


def loc(c, shifts):
    out = []
    for p in c.strip().split('|'):
        m = re.match(r'structural_full/[0-9a-f]+_([\w.]+):(.*)$', p)
        if not m: out.append(p); continue
        r = m[2]
        for f, frm, d in shifts:
            if m[1] == f:
                r = re.sub(r'(\d+)\.(\d+)', lambda k: str(int(k[1]) - d * (int(k[1]) >= frm)) + '.' + k[2], r)
        out.append(m[1] + ':' + r)
    return '|'.join(out)


def parse(x, shifts):
    st, dec = [], {}
    for l in x.splitlines():
        code, _, c = l.partition('  //'); code = code.strip(); ids = ID.findall(code)
        if not ids: continue
        if re.match(r'(wire|reg)\b', code): dec[ids[0]] = ID.sub('@', code)
        st.append((ID.sub(lambda m: '@' + nid(m[0]), code) + ' // ' + loc(c, shifts), ids))
    return st, dec


def refine(S, c, fix):
    inc = collections.defaultdict(list)
    for sh, ids in S:
        sig = h(sh, [fix.get(t, c[t]) for t in ids])
        for p, t in enumerate(ids): inc[t].append((sig, p))
    return {t: (fix[t] if t in fix else h(c[t], sorted(inc[t]))) for t in c}


def num(t): return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', t)]


def pair(O, C, shifts):
    """Net pairing: stable names seed it; colour refinement over statements (shape + source location + operands) pairs
    what is unique on both sides; equal-colour groups of equal size pair in number order (bind numbers are monotonic);
    the rest aligns by the numbered sequence.  Never trusted alone: `residual` below is the proof."""
    A, da = parse(O, ()); B, db = parse(C, shifts)
    init = lambda S, d: {t: h(nid(t), d.get(t, '')) for _, ids in S for t in ids}
    ca, cb = init(A, da), init(B, db); fw, bw = {}, {}
    for t in ca:
        if t in cb and not HASHED.search(t): fw[t] = t; bw[t] = t
    def groups(c, done):
        g = collections.defaultdict(list)
        for t, x in c.items():
            if t not in done: g[x].append(t)
        return g
    def step(ordered):
        nonlocal ca, cb
        ca = refine(A, ca, {u: 'M' + u for u in fw}); cb = refine(B, cb, {v: 'M' + u for v, u in bw.items()})
        ga, gb = groups(ca, fw), groups(cb, bw); n = 0
        for x, L in ga.items():
            R = gb.get(x, [])
            if len(L) == len(R) and (ordered or len(L) == 1):
                for u, v in zip(sorted(L, key=num), sorted(R, key=num)): fw[u] = v; bw[v] = u; n += 1
        return n
    for _ in range(24):
        if not step(False) and not step(True): break
    # what is left sits next to the source change: align by number order, net width and driver shape
    drv = lambda S: {i[0]: s for s, i in S if s.startswith('assign') and i}
    for _ in range(4):
        ua = sorted((t for t in ca if t not in fw), key=num); ub = sorted((t for t in cb if t not in bw), key=num)
        ka = [(nid(t), da.get(t, '')) for t in ua]; kb = [(nid(t), db.get(t, '')) for t in ub]
        sm = difflib.SequenceMatcher(None, ka, kb, autojunk=False); n = 0
        for b in sm.get_matching_blocks():
            for k in range(b.size): fw[ua[b.a + k]] = ub[b.b + k]; bw[ub[b.b + k]] = ua[b.a + k]; n += 1
        if not n: break
    return fw


def lines(x, fw=None):
    r = (lambda l: ID.sub(lambda m: fw.get(m[0], m[0]), l)) if fw else (lambda l: l)
    return collections.Counter(re.sub(r'\s+', ' ', r(l.partition('  //')[0])).strip() for l in x.splitlines())


def residual(x, y, fw):
    a, b = lines(x, fw), lines(y)
    return sorted((a - b).elements()), sorted((b - a).elements())


def token_map(fw):
    """The tokens the four reference transforms use, by scope, old -> new.  A token with no paired net refuses."""
    m = dict(hash={}, att={}, eng={}, procmux={})
    for u, v in fw.items():
        for a, b in zip(re.findall(r'src_([0-9a-f]{20})', u), re.findall(r'src_([0-9a-f]{20})', v)): m['hash'][a] = b
        x = re.fullmatch(re.escape(E) + r'(\d+)_Y', u); y = re.fullmatch(re.escape(E) + r'(\d+)_Y', v)
        if x and y: m['eng'][x[1]] = y[1]; continue
        x = re.fullmatch(re.escape(P) + r'(\d+)_Y', u); y = re.fullmatch(re.escape(P) + r'(\d+)_Y', v)
        if x and y: m['att'][x[1]] = y[1]
        x = re.search(r'procmux_(\d+)_Y$', u); y = re.search(r'procmux_(\d+)_Y$', v)
        if x and y: m['procmux'][x[1]] = y[1]
    used = dict(hash={}, att={}, eng={}, procmux={})
    for p in CL.REF.values():
        src = p.read_text()
        for s, k in ((CL.RE_HASH, 'hash'), (CL.RE_PROC, 'procmux'), (CL.RE_ENG, 'eng')):
            for t in s.findall(src):
                if t not in m[k]: raise ValueError('reference %s token %s has no paired net' % (k, t))
                used[k][t] = m[k][t]
        for t in CL.RE_ATT.findall(src):
            t = t[0] or t[1]
            if t in ('0', '1'): continue
            if t not in m['att']: raise ValueError('reference net %s_Y has no paired net' % t)
            used['att'][t] = m['att'][t]
    return used


def closed(s, ref, rm):
    box = {}
    def run():
        try: box['r'] = CL.close_type(s, ref, rm)
        except Exception as e: box['e'] = e
    threading.stack_size(512 * 1024 * 1024); t = threading.Thread(target=run); t.start(); t.join()
    if 'e' in box: raise box['e']
    return box['r']


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('bound'); ap.add_argument('out')
    ap.add_argument('--old-line-shift', action='append', default=['dsdv_svc_att.sv:451:1'])
    a = ap.parse_args()
    C = Path(a.bound).read_text(); O = CL.ref_text(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    shifts = [(f, int(n), int(d)) for f, n, d in (x.split(':') for x in dict.fromkeys(a.old_line_shift))]
    fw = pair(O, C, shifts); ra, rb = residual(O, C, fw); um = token_map(fw)
    new = {v for k in ('att', 'eng') for v in um[k].values()}
    names = set()
    for k, v in um['att'].items(): names.add(P + v + '_Y')
    for k, v in um['eng'].items(): names.add(E + v + '_Y')
    for k, v in um['procmux'].items(): names.add('procmux_%s_Y' % v)
    for k, v in um['hash'].items(): names.add('src_' + v)
    touched = sorted(n for n in names if any(n in l for l in ra + rb))
    rep = dict(reference=hashlib.sha256(C.encode()).hexdigest(), t7_original=CL.T7_ORIG,
               paired=len(fw), renamed=sum(u != v for u, v in fw.items()), residual=[len(ra), len(rb)], tokens_in_residual=touched,
               tokens={k: len(v) for k, v in um.items()})
    print(json.dumps({k: v for k, v in rep.items() if k != 'reference'}), flush=True)
    (out / 'residual.txt').write_text('\n'.join(['- ' + l for l in ra] + ['+ ' + l for l in rb]) + '\n')
    if touched: sys.exit('REFUSED: reference tokens in the residual: %s' % touched[:20])
    co, _ = closed(O, O, None)
    if not CL.sha(co).startswith(CL.T7_CLOSURE): sys.exit('SELF-CHECK FAIL: %s' % CL.sha(co)[:8])
    print('SELF-CHECK PASS', CL.sha(co)[:8], flush=True)
    cc, rp = closed(C, C, um)
    fwc = dict(fw); ca, cb = residual(co, cc, fwc)
    rep['closure'] = dict(sha=CL.sha(cc), steps=rp['steps'], residual=[len(ca), len(cb)], same_as_preimage=(ca == ra and cb == rb))
    print('CLOSURE', CL.sha(cc)[:8], rep['closure']['residual'], 'same_as_preimage', rep['closure']['same_as_preimage'], flush=True)
    (out / 'residual_closed.txt').write_text('\n'.join(['- ' + l for l in ca] + ['+ ' + l for l in cb]) + '\n')
    if not rep['closure']['same_as_preimage']: sys.exit('REFUSED: closed residual differs from the preimage residual')
    rep['map'] = um
    with gzip.GzipFile(out / 'ref_t7_bound.sv.gz', 'wb', mtime=0) as f: f.write(C.encode())
    (out / 'ref_map.json').write_text(json.dumps(rep, indent=1, sort_keys=True) + '\n')
    print('WROTE', out, flush=True)


if __name__ == '__main__':
    main()
