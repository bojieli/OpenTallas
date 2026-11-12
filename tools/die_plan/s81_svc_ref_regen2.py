#!/usr/bin/env python3
"""Regenerate the svc memory-closure reference when the svc source moved more than one line shift
(VL3-S81-SVCSTN 11-12, COORD ruling 2: ref_1112 for the r11r source -- provider form A, SRX relay stages, H8 fold).

s81_svc_ref_regen.py pairs the nets of the T7 original 61c902f1 and a current T7 bound and PROVES the pairing (residual
free of every token the four transforms use; T7 self-check 12605dc2; the ported chain on the current T7 leaves the same
residual as its preimage).  Its pairing seeds only on stable names and one --old-line-shift, which no longer finds the
pairs after 38 svc/hdc files moved.  This wrapper changes only how the pairing is FOUND; the proofs are the tool's own,
unchanged, and decide:
  * exact per-file source line map (difflib old -> new over the svc source files at the 61c902f1 bind and now);
  * --drop-loc FILE: a file whose old text is unknown keeps the column, not the line, on both sides;
  * register / cell anchors: a register or native cell with the same name on both sides pairs its D, Q and output nets;
  * pass 2: pairs implied by pass-1 register / cell pairs (the bind names Q / Y after the cell) seed a second pass;
  * pass 3 (unify): an unmatched statement whose shape equals one unmatched statement on the other side (paired
    tokens renamed, loose tokens wild) pairs its loose tokens; modes all / def / any, to a fixpoint.
The current bound is first put in closure canonical form (s81_svc_memory_closure.canon_h8), the form close_type
maps every type in.

usage: s81_svc_ref_regen2.py CURRENT_T7_BOUND OUT_DIR --old-src DIR --new-src DIR [--drop-loc FILE ...]
         [--modes all,def,any,def]
OLD/NEW_SRC hold same-named copies of the svc source files (dsdv_svc_att.sv, dsdv_svc_rs.sv) at the two binds.
"""
import argparse, collections, difflib, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_svc_ref_regen as RG          # noqa: E402
import s81_svc_memory_closure as CL     # noqa: E402

LM, DROP, MODES = {}, set(), ['all', 'def', 'any', 'def']


def line_map(old_dir, new_dir):
    out = {}
    for f in sorted(Path(old_dir).iterdir()):
        n = Path(new_dir) / f.name
        if not n.exists(): continue
        a = f.read_text().splitlines(); b = n.read_text().splitlines(); m = {}
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if tag == 'equal':
                for k in range(j2 - j1): m[j1 + k + 1] = i1 + k + 1
        out[f.name] = m
        print('linemap', f.name, 'old', len(a), 'new', len(b), 'mapped', len(m), flush=True)
    return out


def loc(c, shifts):
    out = []
    for p in c.strip().split('|'):
        mm = re.match(r'structural_full/[0-9a-f]+_([\w.]+):(.*)$', p)
        if not mm: out.append(p); continue
        r = mm[2]
        if mm[1] in DROP:
            r = re.sub(r'\d+\.(\d+)', r'L.\1', r)
        elif shifts and mm[1] in LM:
            lm = LM[mm[1]]
            r = re.sub(r'(\d+)\.(\d+)', lambda k: (str(lm[int(k[1])]) if int(k[1]) in lm else 'X' + k[1]) + '.' + k[2], r)
        out.append(mm[1] + ':' + r)
    return '|'.join(out)


def anchors(O, C):
    """register-anchored seeds: a register (g_..._q) with the same name in both bounds pairs its Q alias wire
    (assign W = REG;) and its D net (always ... REG <= N;) when both sides have exactly one."""
    def side(X):
        q, d = {}, {}
        for m in re.finditer(r'assign (w_\w+) = (g_\w+_q);', X): q.setdefault(m[2], []).append(m[1])
        for m in re.finditer(r'always @\(posedge clk\) (g_\w+_q) <= (w_\w+?)(?:\[[^\]]*\])?;', X): d.setdefault(m[1], []).append(m[2])
        y = {}
        for m in re.finditer(r'(ot_bind_native_[0-9a-f]+) (g_\w+) \((.*)\);', X):
            for pn, net in re.findall(r'\.(Y|RD_DATA)\((w_\w+?)(?:\[[^\]]*\])?\)', m[3]):
                y.setdefault((m[1], m[2], pn), []).append(net)
        return q, d, y
    (qo, do, yo), (qc, dc, yc) = side(O), side(C)
    seed = {}
    for a, b in ((qo, qc), (do, dc), (yo, yc)):
        for r, L in a.items():
            if len(L) == 1 and len(b.get(r, [])) == 1: seed[L[0]] = b[r][0]
    inv = {}
    for u, v in seed.items(): inv.setdefault(v, []).append(u)
    return {u: v for u, v in seed.items() if len(inv[v]) == 1}


def pair_reg(O, C, shifts):
    """two passes: pass 1 pairs; pass 2 re-pairs with consistency seeds -- a paired register g_A_q -> g_B_q pairs its
    Q wire and D net, a paired cell instance g_A -> g_B pairs its output nets (the bind names them after the cell)."""
    fw1 = pair_once(O, C, shifts, {})
    def dmap(X):
        d = {}
        for m in re.finditer(r'always @\(posedge clk\) (g_\w+_q) <= (w_\w+?)(?:\[[^\]]*\])?;', X): d.setdefault(m[1], []).append(m[2])
        q = {}
        for m in re.finditer(r'assign (w_\w+) = (g_\w+_q);', X): q.setdefault(m[2], []).append(m[1])
        y = {}
        for m in re.finditer(r'ot_bind_native_[0-9a-f]+ (g_\w+) \((.*)\);', X):
            for pn, net in re.findall(r'\.(Y|RD_DATA)\((w_\w+?)(?:\[[^\]]*\])?\)', m[2]): y.setdefault((m[1], pn), []).append(net)
        return d, q, y
    (do, qo, yo), (dc, qc, yc) = dmap(O), dmap(C)
    seed = {}
    for u, v in fw1.items():
        for a, b in ((do, dc), (qo, qc)):
            if len(a.get(u, [])) == 1 and len(b.get(v, [])) == 1: seed[a[u][0]] = b[v][0]
        for pn in ('Y', 'RD_DATA'):
            if len(yo.get((u, pn), [])) == 1 and len(yc.get((v, pn), [])) == 1: seed[yo[(u, pn)][0]] = yc[(v, pn)][0]
    inv = {}
    for u, v in seed.items(): inv.setdefault(v, []).append(u)
    seed = {u: v for u, v in seed.items() if len(inv[v]) == 1}
    bad = sum(1 for u, v in seed.items() if fw1.get(u) not in (None, v))
    print('pass2 consistency seeds', len(seed), 'disagree with pass 1', bad, flush=True)
    fw = pair_once(O, C, shifts, seed)
    for mode in MODES:
        fw = unify(O, C, fw, mode)
    return fw


def unify(O, C, fw, MODE='all'):
    """pass 3: a statement left unmatched on both sides whose shape is the same once paired tokens are renamed and
    unpaired tokens are wildcards, unique on each side, pairs its unpaired tokens positionally (old unpaired <->
    new unpaired only; a token paired elsewhere is never moved).  Iterated to a fixpoint."""
    import collections
    ID = RG.ID
    def stm(X):
        out = []
        for l in X.splitlines():
            code = l.partition('  //')[0].strip()
            if ID.search(code): out.append(code)
        return out
    So, Sc = stm(O), stm(C); tot = 0
    for _ in range(30):
        bw = {v: u for u, v in fw.items()}
        ren = lambda l: ID.sub(lambda m: fw.get(m[0], m[0]), l)
        cc = collections.Counter(Sc); ro = collections.Counter(ren(l) for l in So)
        uo = [l for l in So if not cc[ren(l)]]; uc = [l for l in Sc if not ro[l]]
        # a token is loose when every statement that names it is unmatched (on its side)
        allo, allc = collections.Counter(), collections.Counter()
        for l in So: allo.update(set(ID.findall(l)))
        for l in Sc: allc.update(set(ID.findall(l)))
        inu_o, inu_c = collections.Counter(), collections.Counter()
        for l in uo: inu_o.update(set(ID.findall(l)))
        for l in uc: inu_c.update(set(ID.findall(l)))
        def defs(U):
            d = set()
            for l in U:
                if l.startswith(('assign ', 'always ')):
                    ids = ID.findall(l)
                    if ids: d.add(ids[0])
            return d
        if MODE == 'any':
            loose_o, loose_c = set(inu_o), set(inu_c)
        elif MODE == 'def':
            loose_o = {t for t in inu_o if inu_o[t] == allo[t]} | defs(uo)
            loose_c = {t for t in inu_c if inu_c[t] == allc[t]} | defs(uc)
        else:
            loose_o = {t for t in inu_o if inu_o[t] == allo[t]}
            loose_c = {t for t in inu_c if inu_c[t] == allc[t]}
        ko, kc = collections.defaultdict(list), collections.defaultdict(list)
        for l in uo:
            ko[ID.sub(lambda m: '?' if (m[0] not in fw or m[0] in loose_o) else fw[m[0]], l)].append(l)
        for l in uc:
            kc[ID.sub(lambda m: '?' if (m[0] not in bw or m[0] in loose_c) else m[0], l)].append(l)
        n = 0
        for key, L in ko.items():
            R = kc.get(key, [])
            if len(L) != 1 or len(R) != 1 or '?' not in key: continue
            a = [t for t in ID.findall(L[0]) if t not in fw or t in loose_o]
            b = [t for t in ID.findall(R[0]) if t not in bw or t in loose_c]
            if len(a) != len(b): continue
            pr = {}; ok = True
            for u, v in zip(a, b):
                if pr.get(u, v) != v or RG.nid(u) != RG.nid(v): ok = False; break
                pr[u] = v
            if not ok or len(set(pr.values())) != len(pr) or all(fw.get(u) == v for u, v in pr.items()): continue
            for u, v in pr.items():
                if fw.get(u) == v: continue
                if u in fw: bw.pop(fw[u], None)
                if v in bw: fw.pop(bw[v], None)
                fw[u] = v; bw[v] = u; n += 1
        tot += n
        if not n: break
    print('pass3 unify paired', tot, flush=True)
    return fw


def pair_once(O, C, shifts, extra):
    """RG.pair with register-anchored seeds (see anchors) added to the stable-name seeds.  Never trusted alone: the
    tool's residual and closure proofs judge the result."""
    import collections, difflib
    A, da = RG.parse(O, ()); B, db = RG.parse(C, shifts)
    nid, h, refine, num = RG.nid, RG.h, RG.refine, RG.num
    init = lambda S, d: {t: h(nid(t), d.get(t, '')) for _, ids in S for t in ids}
    ca, cb = init(A, da), init(B, db); fw, bw = {}, {}
    for t in ca:
        if t in cb and not RG.HASHED.search(t): fw[t] = t; bw[t] = t
    for u, v in list(anchors(O, C).items()) + list(extra.items()):
        if u in ca and v in cb and u not in fw and v not in bw: fw[u] = v; bw[v] = u
    print('anchors seeded', len(fw), flush=True)
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
    for _ in range(4):
        ua = sorted((t for t in ca if t not in fw), key=num); ub = sorted((t for t in cb if t not in bw), key=num)
        ka = [(nid(t), da.get(t, '')) for t in ua]; kb = [(nid(t), db.get(t, '')) for t in ub]
        sm = difflib.SequenceMatcher(None, ka, kb, autojunk=False); n = 0
        for b in sm.get_matching_blocks():
            for k in range(b.size): fw[ua[b.a + k]] = ub[b.b + k]; bw[ub[b.b + k]] = ua[b.a + k]; n += 1
        if not n: break
    return fw


def main():
    global LM, DROP, MODES
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('bound'); ap.add_argument('out')
    ap.add_argument('--old-src', required=True); ap.add_argument('--new-src', required=True)
    ap.add_argument('--drop-loc', action='append', default=[])
    ap.add_argument('--modes', default='all,def,any,def')
    a = ap.parse_args()
    LM = line_map(a.old_src, a.new_src); DROP = set(a.drop_loc); MODES = a.modes.split(',')
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    canon = out / 'current_t7_canon.sv'
    canon.write_text(CL.canon_h8(Path(a.bound).read_text()))
    RG.loc = loc; RG.pair = pair_reg
    sys.argv = ['s81_svc_ref_regen.py', str(canon), str(out), '--old-line-shift', 'none:0:0']
    try:
        RG.main()
    finally:
        canon.unlink()


if __name__ == '__main__':
    main()
