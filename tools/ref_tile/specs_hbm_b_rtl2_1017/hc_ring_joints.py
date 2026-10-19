#!/usr/bin/env python3
"""HCRING 10-19: physical bit order across the 8 HC ring bank joints, from the bank kit pin plans (or routed LEFs).

    hc_ring_joints.py [--rev REV] [--mode plan|chunk32] [--lef KIT=view.lef ...] --out J.json [--svh DIR]

Ring (tools/ref_tile/specs_hbm_b_rtl2_1017/mk_ring_kits.py): 3 x 3 cells of 734.4 um, hub in the centre; chain
b0 W -> b1 NW -> b2 N -> b3 NE -> b4 E -> b5 SE -> b6 S -> b7 SW -> b0 (S face, chain exit s_i).  Masters: b0 = b0,
ca = b1 / b5, e2 = b2 / b6, cb = b3 / b7, e0 = b4; the S row (b5, b6, b7) is placed R180.

Pin model (what the route does with the kit):
  plan     route.pin_balance in the kit: bit k of a ranged port at lo + (hi - lo)(k + .5)/n, high bit first for
           pin_order_desc ports (run_abi3_physical OT_PIN_ORDER_DESC).  A kit WITHOUT pin_balance is modelled as an
           ideally ordered ascending group (the best case of PPL -group -order) and flagged order_defined=false.
  chunk32  kits without pin_balance as the route really places them: OT_PIN_GROUP_MAX 32 chunks scattered over the
           region (fixed-seed shuffle; the closed hbfd_rly_1136_WE view has 13 descents in 1,136 bits).
  --lef    the routed view's real pin centres for that kit (re-check after the routes close).
Joint wiring = what abutted (or channel-routed, crossing-free) faces give: the two face pin rows paired by rank along
the joint line.  Per link the report gives the permutation (input bit <- output bit), identity yes/no, crossings of a
name-wired connection (inversions) and the largest position offset.  --svh writes hc_joint_map.svh for
rtl/test/run_hbm_hc_eng4_ring.sh (HC_JOINT_MAP=DIR): the HC lockstep then runs on the physically wired ring.
Face vector (ot_hbm_hc_qeng_static fo / fi, 2,078 b, face-position order): v 0, ss 1, nv 2-8, wa 9-18, xa 19-28,
sum 29-2076, f 2077; link 8 uses sum + f only (b0 s_i = {f, sum}).
"""
import argparse, json, random, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
S = 734.4
CELL = {0: (0, 1, 'R0'), 1: (0, 2, 'R0'), 2: (1, 2, 'R0'), 3: (2, 2, 'R0'), 4: (2, 1, 'R0'),
        5: (2, 0, 'R180'), 6: (1, 0, 'R180'), 7: (0, 0, 'R180')}
MASTER = {0: 'b0', 1: 'ca', 2: 'e2', 3: 'cb', 4: 'e0', 5: 'ca', 6: 'e2', 7: 'cb'}
FIELDS = [('v', 1), ('ss', 1), ('nv', 7), ('wa', 10), ('xa', 10), ('sum', 2048), ('f', 1)]
OUTP = dict(v='o_v', ss='o_ss', nv='o_nv', wa='o_wa', xa='o_xa', sum='sum_out', f='f_out')
INP = dict(v='d_v', ss='d_ss', nv='d_nv', wa='d_wa', xa='d_xa', sum='sum_in', f='f_in')
FV = sum(w for _, w in FIELDS)
OFF = {}
_o = 0
for _n, _w in FIELDS:
    OFF[_n] = _o
    _o += _w


def spec(kit, rev):
    rel = f'physical/ref_tile/hbm_hcq_bank_{kit}_1017/spec.json'
    if rev:
        return json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{rev}:{rel}'], text=True))
    return json.loads((ROOT / rel).read_text())


def lef_pins(path):
    import re
    t = Path(path).read_text()
    out = {}
    for m in re.finditer(r'PIN (\S+)\n(.*?)END (\S+)\n', t, re.S):
        r = re.search(r'RECT\s+([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)', m.group(2))
        if r:
            x0, y0, x1, y1 = map(float, r.groups())
            out[m.group(1)] = ((x0 + x1) / 2, (y0 + y1) / 2)
    return out


class Kit:
    def __init__(self, kit, rev, mode, lef):
        self.kit, self.s = kit, spec(kit, rev)
        self.face = {n: f for f, ns in self.s['pins'].items() for n in ns}
        self.bal = bool(self.s.get('route', {}).get('pin_balance'))
        self.desc = set(self.s.get('pin_order_desc') or [])
        self.mode, self.lef = mode, (lef_pins(lef) if lef else None)

    def pos(self, port, n):
        """[(face, t along the face from its left / bottom end)] for bits 0..n-1 of port, master coordinates"""
        f = self.face[port]
        if self.lef:
            out = []
            for k in range(n):
                x, y = self.lef[f'{port}[{k}]' if n > 1 else port]
                out.append((f, x if f in 'NS' else y))
            return out
        lo, hi = self.s['pin_ranges'][port]
        order = list(range(n))
        if port in self.desc:
            order = order[::-1]
        if not self.bal and self.mode == 'chunk32' and n > 32:
            ch = [order[i:i + 32] for i in range(0, n, 32)]
            random.Random(f'{self.kit}:{port}').shuffle(ch)
            order = [b for c in ch for b in c]
        t = [0.0] * n
        for slot, b in enumerate(order):
            t[b] = lo + (hi - lo) * (slot + 0.5) / n
        return [(f, t[k]) for k in range(n)]


def die_xy(bank, face, t):
    cx, cy, o = CELL[bank]
    X, Y = cx * S, cy * S
    x, y = {'N': (t, S), 'S': (t, 0.0), 'W': (0.0, t), 'E': (S, t)}[face]
    if o == 'R180':
        x, y = S - x, S - y
    return X + x, Y + y


def inversions(a):
    """pairs i < j with a[i] > a[j] (merge sort)"""
    def rec(v):
        if len(v) < 2:
            return v, 0
        m = len(v) // 2
        l, x = rec(v[:m])
        r, y = rec(v[m:])
        out, i, j, c = [], 0, 0, x + y
        while i < len(l) and j < len(r):
            if l[i] <= r[j]:
                out.append(l[i]); i += 1
            else:
                out.append(r[j]); j += 1; c += len(l) - i
        out += l[i:] + r[j:]
        return out, c
    return rec(list(a))[1]


def link(kits, k):
    a, b = k - 1, k % 8
    src, dst = kits[MASTER[a]], kits[MASTER[b]]
    fields = FIELDS if k < 8 else [('sum', 2048), ('f', 1)]
    sp, dp = {}, {}                                   # face-vector index -> die point
    for n, w in fields:
        for i, (f, t) in enumerate(src.pos(OUTP[n], w)):
            sp[OFF[n] + i] = die_xy(a, f, t)
        if k < 8:
            for i, (f, t) in enumerate(dst.pos(INP[n], w)):
                dp[OFF[n] + i] = die_xy(b, f, t)
    if k == 8:                                        # b0 s_i = {f, sum[2047:0]}
        for i, (f, t) in enumerate(dst.pos('s_i', 2049)):
            dp[(OFF['f'] if i == 2048 else OFF['sum'] + i)] = die_xy(b, f, t)
    axis = 0 if abs(sp[OFF['sum']][1] - sp[OFF['sum'] + 1][1]) < 1e-6 else 1    # joint runs along x (N/S) or y
    line_s = {round(p[1 - axis], 3) for p in sp.values()}
    line_d = {round(p[1 - axis], 3) for p in dp.values()}
    abut = line_s == line_d and len(line_s) == 1
    idx = sorted(sp)
    rs = sorted(idx, key=lambda i: sp[i][axis])
    rd = sorted(idx, key=lambda i: dp[i][axis])
    perm = {d: s for d, s in zip(rd, rs)}            # input bit d <- output bit s (rank pairing, crossing-free)
    ident = all(perm[i] == i for i in idx)
    off = max(abs(dp[i][axis] - sp[i][axis]) for i in idx)
    inv = inversions([dp[i][axis] for i in rs])
    return dict(link=k, src=f'b{a} ({MASTER[a]} {CELL[a][2]})', dst=f'b{b} ({MASTER[b]} {CELL[b][2]})',
                bits=len(idx), abutted_faces=abut, identity=ident, moved_bits=sum(perm[i] != i for i in idx),
                name_wired_crossings=inv, max_offset_um=round(off, 3),
                order_defined=src.bal and dst.bal, perm=perm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rev', default='')
    ap.add_argument('--mode', choices=['plan', 'chunk32'], default='plan')
    ap.add_argument('--lef', action='append', default=[], help='KIT=view.lef (KIT in b0 ca cb e0 e2)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--svh', default='')
    ap.add_argument('--tol-um', type=float, default=2.0)
    a = ap.parse_args()
    lefs = dict(x.split('=', 1) for x in a.lef)
    kits = {m: Kit(m, a.rev, a.mode, lefs.get(m)) for m in ('b0', 'ca', 'e2', 'cb', 'e0')}
    links = [link(kits, k) for k in range(1, 9)]
    ok = all(l['identity'] and l['name_wired_crossings'] == 0 and l['max_offset_um'] <= a.tol_um and l['order_defined']
             for l in links)
    tag = f"rev={a.rev or 'worktree'} mode={a.mode} lef={','.join(sorted(lefs)) or '-'} {'PASS' if ok else 'FAIL'}"
    rep = dict(tool='tools/ref_tile/specs_hbm_b_rtl2_1017/hc_ring_joints.py', tag=tag, pass_=ok, tol_um=a.tol_um,
               links=[{k: v for k, v in l.items() if k != 'perm'} for l in links])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    for l in rep['links']:
        print(f"link {l['link']} {l['src']:>14} -> {l['dst']:<14} bits {l['bits']:4d} abut {l['abutted_faces']!s:5} "
              f"identity {l['identity']!s:5} moved {l['moved_bits']:4d} crossings {l['name_wired_crossings']:7d} "
              f"offset {l['max_offset_um']:8.3f} um order_defined {l['order_defined']}")
    print('HC_RING_JOINTS', tag)
    if a.svh:
        d = Path(a.svh)
        d.mkdir(parents=True, exist_ok=True)
        L = [f'// {tag}', '// generated by tools/ref_tile/specs_hbm_b_rtl2_1017/hc_ring_joints.py: fi = physical abutment of fo',
             f'assign fi[0 +: {FV}] = fo[0 +: {FV}];']
        for l in links:
            k, p = l['link'], l['perm']
            src = [p.get(i, i) for i in range(FV)]  # unlisted (link 8 descriptor bits) = unchanged, unread
            L.append(f'assign fi[{k * FV} +: {FV}] = {{' +
                     ', '.join(f'fo[{k * FV + src[i]}]' for i in reversed(range(FV))) + '};')
        (d / 'hc_joint_map.svh').write_text('\n'.join(L) + '\n')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
