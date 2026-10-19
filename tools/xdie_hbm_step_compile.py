#!/usr/bin/env python3
"""XDIE-HBM3 (2026-10-19): compiler for the two-die HBM d4g cross-die collective STEP co-sim with VM-SOURCED operands at
production frame counts (rtl/hbm_accel/generic/collective/xdie/tb_xdie_hbm_step.sv).

One cross-die exchange step, both dies at once (every DS / Qwen cross-die collective is a chain of such steps), lowered to
the actual programmes of the real die elements at compiler cycles:
  * hb_coll_NE (ot_hfd_coll_q2_hard_v8g, NLINK 1): F20 rows of the v4/v5 1536-b ISA (static_uop_layout_v4.json) with
    LOOPS (static_issuer_v6 metadata {next, target, count, halt, lid}, <= 64 rows): steady streams are loop bodies whose
    link sequences / VM sectors / delivery offsets advance by iteration x iter_{link_slot,vm,del}_step (ctl_v5);
  * epcal_NE (hfd_hgi_vm_calendar, 187-b words; ep_N2 RX controls = word[18:0]): arm / static release / drain slots.

TX (both kinds): frame f of the local vector lives in VM bank pair p = f % 4 (banks 2p, 2p+1), sector SB + f // 4.
  VM request v (vm_rq pair tuples + vm_pair_select entry 0 + vm_meta entry 0) -> VM0 capture v+10 -> sink rail0 v+11 ->
  link wr v+13 (seq f) -> link rd on the f-th valid TX beat >= wr + 8 (wr = rd - 8; hfd_ep_static TX calendar).
RX, kind 'ag' (gather step): static release of the landed block, drain slot w_f = rel + 1 + f (one a cycle) -> COLL
  rx_expect ux = K2 + w + 16 - K1 -> rail capture ux+3 -> sink DEL0 ux+4 with delivery offset DB + 64 f.
RX, kind 'rs' (reduce step): per frame two reduce inputs (reduce_static: in_v == load_v | add_read), cadence 2 cycles:
  local operand re-read from VM (request R-13, capture R-3, sink reduce R-2, load R, tag f % 8), peer frame (rx_expect R-5,
  capture R-2, sink reduce R-1, add_read R+1, add_issue R+2), publication read R+11 / issue R+12, reduce source capture
  R+13, sink DEL0 R+14 (offset DB + 64 f).  Result = local + peer (binary32 RNE; a 2-operand sum is order-free, so both
  dies publish the same bits).
Constants measured by the co-sim itself (stage logs, as tools/xdie_hbm_coll_compile.py): K1, K2, gcL, READY.

  xdie_hbm_step_compile.py OUT --kind ag|rs --frames P [--from LOG|-] [--guard G] [--release-early N]
                           [--mut vmstep|flip|rsrc]
"""
import argparse, json, pathlib, random, re, struct, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NPT, ND = 1, 14
SRC_RAIL0, SRC_VM0, SRC_RED = 2, 3, 7               # SU0,SU1,rail0,VM0..3,reduce
DST_RAIL0, DST_DEL0, DST_RED = 0, 1, 13             # rail0,SU/DEL0..3,RGX0..3,TKM0..3,reduce
IDLE_K = 204
VM_CAP, RX_CAP = 10, 3
EPOCH = 0x3b
SB, DB = 16, 0x10000 + 3 * 0x4000
F = dict(capture_slot=(0, 10), sink_slot=(10, 16), sink_select=(26, 64), lk_wr_v=(350, 3), lk_wr_slot=(353, 18),
         lk_rd_v=(371, 3), lk_rd_slot=(374, 18), lk_rx_expect=(392, 3), lk_rx_slot=(395, 18), lk_epoch_begin=(413, 3),
         lk_epoch=(416, 8), del_obase=(874, 160), vm_rq=(1034, 136), vm_meta=(1170, 132), iter_vm_step=(1302, 16),
         iter_del_step=(1350, 16), vm_pair_select=(1383, 24), iter_link_slot_step=(1407, 8),
         lk_wr_seq_high=(1415, 30), lk_rd_seq_high=(1445, 30), lk_rx_seq_high=(1475, 30))
AR = dict(load_v=(0, 1), load_tag=(1, 4), add_read=(5, 1), read_tag=(6, 4), add_issue=(10, 1), pub_read=(11, 1),
          pub_tag_a=(12, 4), pub_release=(21, 1), pub_issue=(22, 1), pub_src=(23, 8), pub_index=(31, 16))
AR_STEP_LSB = 714          # AR_ITER (XDIE-HBM4): reserved ring[87:84] = iter_ar_tag_step (v8g #(.AR_ITER(1)) only)
ORM = ('capture_slot', 'sink_slot', 'sink_select')   # bit-mask fields: several events may share a row


def check_layout():
    lay = json.loads((ROOT / 'rtl/hbm_accel/generic/collective/p2p/static_uop_layout_v4.json').read_text())
    for k, (lsb, w) in F.items():
        f = lay['fields'][k]
        assert (f['lsb'], f['width']) == (lsb, w), (k, f)
    for k, (lsb, w) in AR.items():
        f = lay['ar_fields'][k]
        assert (f['lsb'], f['width']) == (lsb, w), (k, f)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def vec(lanes):
    return sum(bits(v) << (32 * l) for l, v in enumerate(lanes))


def operands(d, P, seed=1019):
    r = random.Random(seed * 7 + d)
    xs = []
    for _ in range(P):
        lanes = []
        for _ in range(16):
            e = r.randint(-9, 9)
            m = 1.0 + r.getrandbits(23) / float(1 << 23)
            lanes.append(f32(r.choice((1.0, -1.0)) * m * 2.0 ** e))
        xs.append(lanes)
    return xs


def gstep(ph, gc):
    if gc == IDLE_K:
        return ph, 0
    if ph == 4:
        return 0, gc + 1
    return ph + 1, gc


def beat_ok(n, gcl):
    ph, gc = 0, gcl
    for _ in range(n):
        ph, gc = gstep(ph, gc)
    return ph != 4 and gc != IDLE_K


def meta33(src, idx):
    return (1 << 32) | (0xff << 24) | (src << 16) | (idx & 0xffff)


class Sched:
    """abstract per-cycle schedule: S = static fields (incl. AR), I = iterated values {wr, rd, rx, vm{bank:sector}, del}"""
    def __init__(self):
        self.S, self.I = {}, {}

    def s(self, u, k, v):
        assert u >= 0, (k, u)
        r = self.S.setdefault(u, {})
        if k in ORM:
            r[k] = r.get(k, 0) | v
        else:
            assert k not in r or r[k] == v, ('field conflict', u, k, r.get(k), v)
            r[k] = v

    def i(self, u, k, v):
        assert u >= 0, (k, u)
        r = self.I.setdefault(u, {})
        assert k not in r or r[k] == v, ('iter conflict', u, k, r.get(k), v)
        r[k] = v

    def ar(self, u, k, v):            # AR_ITER: reduce tag / publication index as the frame number (iterated)
        assert u >= 0, (k, u)
        r = self.I.setdefault(u, {}).setdefault('ar', {})
        assert k not in r or r[k] == v, ('ar conflict', u, k, r.get(k), v)
        r[k] = v

    def seq(self, u, kind, s):        # sequence fields one row BEFORE the reservation (ctl_v5 registers them)
        self.i(u - 1, kind, s)

    def vm(self, u, f, d, sector_of):
        p = f % 4
        r = self.I.setdefault(u, {})
        assert 'vm' not in r, ('one VM read a row', u)
        r['vm'] = {2 * p: sector_of(f), 2 * p + 1: sector_of(f)}
        self.s(u, 'vm_valid', (1 << (2 * p)) | (1 << (2 * p + 1)))
        self.s(u, 'vm_pair_select', ((2 * p + 1) << 3) | (2 * p))
        self.s(u, 'vm_meta', meta33(d, p))

    def key(self, u):
        return tuple(sorted(self.S.get(u, {}).items()))


def compile_die(d, C, kind, P, rel_w, early=0, mut='', ar_iter=False, del_edge=0):
    K1, K2, gcl = C['K1'], C['K2'], C['gcL']
    Sd = Sched()
    Sd.s(0, 'lk_epoch_begin', 1); Sd.s(0, 'lk_epoch', EPOCH)
    sec = lambda f: SB + f // 4
    # ---- TX: frame f -> VM request v, capture v+10, sink rail v+11, wr v+13, rd on the f-th valid beat >= wr + 8
    rd, u = [], 22
    while len(rd) < P:
        if beat_ok(K1 + u + 18, gcl):
            rd.append(u)
        u += 1
    tx = []
    for f, ur in enumerate(rd):
        w = ur - 8; v = w - 13
        Sd.vm(v, f, d, sec)
        Sd.s(v + VM_CAP, 'capture_slot', 1 << SRC_VM0)
        Sd.s(v + VM_CAP + 1, 'sink_slot', 1 << DST_RAIL0); Sd.s(v + VM_CAP + 1, 'sink_select', SRC_VM0 << (4 * DST_RAIL0))
        Sd.s(w, 'lk_wr_v', 1); Sd.seq(w, 'wr', f)
        Sd.s(ur, 'lk_rd_v', 1); Sd.seq(ur, 'rd', f)
        tx.append(dict(f=f, vm=v, wr=w, rd=ur))
    # ---- RX calendar: arm bank 0 with P words at word 0, static release rel_w, drain slots after it
    rel_w = rel_w - early
    assert 1 <= P <= 64, P
    cal = {0: (1 << 0) | (0 << 1) | (P << 2)}
    cal[rel_w] = cal.get(rel_w, 0) | (1 << 9)
    ux_of = lambda w: K2 + w + 16 - K1
    rx, pub = [], []
    if kind == 'ag':
        for f in range(P):
            w = rel_w + 1 + f; ux = ux_of(w)
            cal[w] = cal.get(w, 0) | (1 << 11) | (0 << 12) | (f << 13)
            Sd.s(ux, 'lk_rx_expect', 1); Sd.seq(ux, 'rx', f)
            Sd.s(ux + RX_CAP, 'capture_slot', 1 << SRC_RAIL0)
            Sd.s(ux + RX_CAP + 1, 'sink_slot', 1 << DST_DEL0); Sd.s(ux + RX_CAP + 1, 'sink_select', SRC_RAIL0 << (4 * DST_DEL0))
            Sd.i(ux + RX_CAP + 1 + del_edge, 'del', DB + 64 * f)
            rx.append(dict(f=f, w=w, ux=ux)); pub.append(ux + RX_CAP + 1)
    else:
        R0 = K2 + (rel_w + 1) + 16 - K1 + 5
        for f in range(P):
            R = R0 + 2 * f; ux = R - 5; w = ux - K2 - 16 + K1; tag = f % 8
            assert w > rel_w
            cal[w] = cal.get(w, 0) | (1 << 11) | (0 << 12) | (f << 13)
            fl = f
            if mut == 'rsrc' and d == 1 and f == 1:
                fl = f + 4                     # local operand read from frame f+4's sector (same bank pair): wrong data
            Sd.vm(R - 13, f, d, lambda _f, fl=fl: sec(fl))
            Sd.s(R - 3, 'capture_slot', 1 << SRC_VM0)
            Sd.s(R - 2, 'sink_slot', 1 << DST_RED); Sd.s(R - 2, 'sink_select', SRC_VM0 << (4 * DST_RED))
            Sd.s(R, 'load_v', 1)
            tg = (lambda u, k, ff=f: Sd.ar(u, k, ff)) if ar_iter else (lambda u, k, t=tag: Sd.s(u, k, t))
            tg(R, 'load_tag')
            Sd.s(ux, 'lk_rx_expect', 1); Sd.seq(ux, 'rx', f)
            Sd.s(ux + RX_CAP, 'capture_slot', 1 << SRC_RAIL0)
            Sd.s(R - 1, 'sink_slot', 1 << DST_RED); Sd.s(R - 1, 'sink_select', SRC_RAIL0 << (4 * DST_RED))
            Sd.s(R + 1, 'add_read', 1); tg(R + 1, 'read_tag')
            Sd.s(R + 2, 'add_issue', 1)
            Sd.s(R + 11, 'pub_read', 1); tg(R + 11, 'pub_tag_a'); Sd.s(R + 11, 'pub_release', 1)
            Sd.s(R + 11, 'pub_src', d)
            if ar_iter:
                Sd.ar(R + 11, 'pub_index', f)
            else:
                Sd.s(R + 11, 'pub_index', f % 8)
            Sd.s(R + 12, 'pub_issue', 1)
            Sd.s(R + 13, 'capture_slot', 1 << SRC_RED)
            Sd.s(R + 14, 'sink_slot', 1 << DST_DEL0); Sd.s(R + 14, 'sink_select', SRC_RED << (4 * DST_DEL0))
            Sd.i(R + 14 + del_edge, 'del', DB + 64 * f)
            rx.append(dict(f=f, w=w, ux=ux, R=R)); pub.append(R + 14)
    end = max(max(Sd.S), max(Sd.I)) + 3
    return dict(S=Sd, end=end, tx=tx, rx=rx, pub=pub, rel_w=rel_w, cal=cal)


# ---------------------------------------------------------------- lowering with loops
SEQK = ('wr', 'rd', 'rx')


def steps_between(a, b):
    """iterated values a (iteration m) -> b (m + 1): per-row steps (k, vm, del, ar) or None when not one consistent step"""
    if set(a) != set(b):
        return None
    k = {b[x] - a[x] for x in SEQK if x in a}
    if len(k) > 1:
        return None
    k = k.pop() if k else 0
    if not 0 <= k < 256:
        return None
    sv = 0
    if 'vm' in a:
        if set(a['vm']) != set(b['vm']):
            return None
        s = {b['vm'][bk] - a['vm'][bk] for bk in a['vm']}
        if len(s) != 1:
            return None
        sv = s.pop()
        if not 0 <= sv < 65536:
            return None
    dv = 0
    if 'del' in a:
        dv = b['del'] - a['del']
        if not 0 <= dv < 65536:
            return None
    sa = 0
    if 'ar' in a:                         # AR_ITER: every reduce tag + the publication index advance by ONE 4-bit step
        if set(a['ar']) != set(b['ar']):
            return None
        s = {b['ar'][x] - a['ar'][x] for x in a['ar']}
        if len(s) != 1:
            return None
        sa = s.pop()
        if not 0 <= sa < 16:
            return None
    return (k, sv, dv, sa)


def lower(Sd, end, cap=64):
    keys = [Sd.key(u) for u in range(end + 1)]
    its = [Sd.I.get(u, {}) for u in range(end + 1)]
    rows = []                               # (static dict, iter base dict, steps, meta extras)
    u = 0
    while u <= end:
        best = (0, 1, 1, None)              # saved rows, T, n, steps
        for T in range(1, 33):
            if u + 2 * T - 1 > end - 1:
                break
            st = []
            ok = True
            for i in range(T):
                if keys[u + i] != keys[u + i + T]:
                    ok = False; break
                s = steps_between(its[u + i], its[u + i + T])
                if s is None:
                    ok = False; break
                st.append(s)
            if not ok:
                continue
            n = 2
            while u + (n + 1) * T - 1 <= end - 1:
                good = True
                for i in range(T):
                    a, b = u + i + (n - 1) * T, u + i + n * T
                    if keys[a] != keys[b] or steps_between(its[a], its[b]) != st[i]:
                        good = False; break
                if not good:
                    break
                n += 1
            saved = (n - 1) * T
            if saved > best[0]:
                best = (saved, T, n, st)
        saved, T, n, st = best
        if n == 1:
            rows.append(dict(u=u, T=1, n=1, step=(0, 0, 0, 0), body_start=None))
            u += 1
            continue
        r0 = len(rows)
        for i in range(T):
            rows.append(dict(u=u + i, T=T, n=n, step=st[i], body_start=r0))
        u += n * T
    lower.nrows = len(rows)
    assert len(rows) <= cap, ('programme capacity', len(rows), cap)
    # metadata: next | target << 6 | count << 12 | halt << 44 | lid << 45; ROWS 128 (cap > 64): pc bit 6 of
    # next / target / lid at 51 / 52 / 53 (ot_hgi_coll_static_issuer_v6 #(ROWS 128))
    pm = 127 if cap > 64 else 63
    pc7 = lambda v, lo, hi: ((v & 63) << lo) | (((v >> 6) & 1) << hi)
    meta, words = [], []
    for r, row in enumerate(rows):
        m = pc7((r + 1) & pm, 0, 51)
        if row['body_start'] is not None:
            last = row['body_start'] + row['T'] - 1
            m |= pc7(last, 45, 53)
            if r == last:
                m |= pc7(row['body_start'], 6, 52) | (row['n'] << 12)
        meta.append(m)
        words.append(encode(Sd, row['u'], row['step']))
    meta[-1] |= 1 << 44
    # independent unroll of the issuer_v6 metadata/counter ISA + the ctl_v5 iteration offsets -> compare every cycle
    pc, cnt = 0, [0] * 128
    fld = lambda m, lo, hi: ((m >> lo) & 63) | (((m >> hi) & 1) << 6)
    for c in range(end + 1):
        m = meta[pc]
        it = cnt[fld(m, 45, 53)]
        row = rows[pc]
        assert Sd.key(row['u']) == keys[c], ('unroll static mismatch', c, pc)
        k, sv, dv, sa = row['step']
        base = Sd.I.get(row['u'], {})
        got = {}
        for x in SEQK:
            if x in base:
                got[x] = base[x] + it * k
        if 'vm' in base:
            got['vm'] = {bk: s + it * sv for bk, s in base['vm'].items()}
        if 'del' in base:
            got['del'] = base['del'] + it * dv
        if 'ar' in base:
            got['ar'] = {x: v + it * sa for x, v in base['ar'].items()}
        assert got == its[c], ('unroll iter mismatch', c, pc, it, got, its[c])
        if m >> 44 & 1:
            assert c == end, ('early halt', c, end)
            break
        count, lid = (m >> 12) & 0xffffffff, fld(m, 45, 53)
        if count and cnt[lid] < count - 1:
            cnt[lid] += 1; pc = fld(m, 6, 52)
        else:
            if count:
                cnt[lid] = 0
            pc = fld(m, 0, 51)
    else:
        raise AssertionError('no halt')
    lower.rowmap = rows
    return words, meta


def encode(Sd, u, step):
    st = dict(Sd.S.get(u, {}))
    base = Sd.I.get(u, {})
    k, sv, dv, sa = step
    w, a = 0, 0

    def put(name, v):
        nonlocal w
        lsb, wd = F[name]
        assert 0 <= v < (1 << wd), (u, name, v)
        w |= v << lsb
    for x in SEQK:
        if x in base:
            put('lk_%s_slot' % x, base[x] & 63); put('lk_%s_seq_high' % x, base[x] >> 6)
    if k:
        put('iter_link_slot_step', k)
    vv = st.pop('vm_valid', 0)
    if vv:
        rq = 0
        for b in range(8):
            if vv >> b & 1:
                rq |= ((1 << 16) | base['vm'][b]) << (17 * b)
        put('vm_rq', rq)
    if sv:
        put('iter_vm_step', sv)
    if 'del' in base:
        put('del_obase', base['del'])
    if dv:
        put('iter_del_step', dv)
    for name, v in base.get('ar', {}).items():   # AR_ITER base values (iteration 0): tags mod 16, index 16 b
        st[name] = v & 15 if name != 'pub_index' else v
    if sa:
        w |= sa << AR_STEP_LSB
    for name, v in st.items():
        if name in AR:
            lsb, wd = AR[name]
            assert 0 <= v < (1 << wd), (u, name, v)
            a |= v << lsb
        else:
            put(name, v)
    if a:
        w |= (a & ((1 << 31) - 1)) << 1505
        w |= (a >> 31) << 688
    return w


def measure(log):
    txt = pathlib.Path(log).read_text() if log != '-' else ''
    M = {0: {}, 1: {}}
    for d in (0, 1):
        g = lambda pat: [tuple(int(x) for x in ((mm,) if isinstance(mm, str) else mm)) for mm in re.findall(pat % d, txt)]
        L = g(r'XDIE2_L d=%d edge=(\d+) ph=(\d+) gc=(\d+)')
        if L:
            M[d]['gcL'] = L[0][2]
        wr = g(r'XDIE2_WR d=%d rel=(-?\d+)')
        arm = g(r'XDIE2_ARM d=%d rel=(-?\d+) bank')
        rdy = g(r'XDIE2_RDY d=%d bank=0 rel=(-?\d+)')
        if wr:
            M[d]['WR_rel'] = wr[0][0]
        if arm:
            M[d]['K2'] = arm[0][0]
        if rdy:
            M[d]['READY'] = rdy[0][0]
    pi = re.search(r'XDIE3_FIRSTWR (\d+) (\d+)', txt)
    M['first_wr_row'] = [int(pi[1]), int(pi[2])] if pi else None
    M['pass'] = bool(re.search(r'^XDIE2 .* PASS$', txt, re.M))
    return M


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'measure':
        print(json.dumps(measure(sys.argv[2]))); return
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('--kind', choices=['ag', 'rs'], required=True)
    ap.add_argument('--frames', type=int, required=True)
    ap.add_argument('--from', dest='frm', default='-')
    ap.add_argument('--k1', type=int, default=11); ap.add_argument('--k2', type=int, default=7)
    ap.add_argument('--gcl', type=int, default=116)
    ap.add_argument('--ready', type=int, default=0, help='assumed READY (rel L) when not measured (0: from --swd)')
    ap.add_argument('--swd', type=int, default=4)
    ap.add_argument('--guard', type=int, default=8)
    ap.add_argument('--release-early', type=int, default=0)
    ap.add_argument('--mut', default='', choices=['', 'vmstep', 'flip', 'rsrc', 'arstep'])
    ap.add_argument('--ar-iter', action='store_true', help='iterated reduce tags (v8g AR_ITER=1, iter_ar_tag_step)')
    ap.add_argument('--del-edge', type=int, default=0, help='XDIE-HBM4 item 3: del_obase row = sink row + N (1: the '
                    'ctl_v5 delivery_obase pin then lands on the DEL0 valid edge; 0 = XDIE-HBM3 programmes)')
    ap.add_argument('--rows', type=int, default=64, choices=[64, 128], help='issuer ROWS (v8g #(.ROWS))')
    a = ap.parse_args()
    check_layout()
    a.out.mkdir(parents=True, exist_ok=True)
    M = measure(a.frm) if a.frm != '-' else {0: {}, 1: {}, 'first_wr_row': None}
    P = a.frames
    xs = [operands(0, P), operands(1, P)]
    plan = {}
    for d in (0, 1):
        m = M[d]
        fw = M.get('first_wr_row')
        K1 = (m['WR_rel'] - fw[d]) if ('WR_rel' in m and fw) else a.k1
        C = dict(K1=K1, K2=m.get('K2', a.k2), gcL=m.get('gcL', a.gcl))
        ready = m.get('READY') or a.ready or (480 + 2 * P + 60 if a.swd > 100 else 150 + 2 * P + 60)
        rel_w = ready + a.guard - C['K2']
        c = compile_die(d, C, a.kind, P, rel_w, early=a.release_early if d == 1 else 0, mut=a.mut, ar_iter=a.ar_iter, del_edge=a.del_edge)
        words, meta = lower(c['S'], c['end'], cap=a.rows)
        rows = lower.rowmap
        if a.mut == 'vmstep' and d == 1:          # TX loop body: VM sector step off by one (wrong frames read)
            hit = [r for r, row in enumerate(rows) if row['step'][1] and row['T'] > 1 and row['u'] < c['tx'][-1]['vm'] + 1]
            assert hit, 'no TX VM loop row to mutate'
            words[hit[0]] ^= ((rows[hit[0]]['step'][1]) ^ (rows[hit[0]]['step'][1] + 1)) << F['iter_vm_step'][0]
        if a.mut == 'arstep' and d == 1:          # RS loop body: iter_ar_tag_step off by one (tags/index of later frames wrong)
            hit = [r for r, row in enumerate(rows) if row['step'][3] and row['T'] > 1]
            assert hit, 'no AR loop row to mutate'
            sa = rows[hit[0]]['step'][3]
            words[hit[0]] ^= (sa ^ ((sa + 1) & 15)) << AR_STEP_LSB
        if a.mut == 'flip' and d == 1:            # first rx_expect reservation bit cleared
            ux = c['rx'][0]['ux']
            r = max(i for i, row in enumerate(rows) if row['u'] <= ux)
            assert words[r] >> F['lk_rx_expect'][0] & 1, r
            words[r] ^= 1 << F['lk_rx_expect'][0]
        lines = []
        for w, mt in zip(words, meta):
            for seg in range(6):
                lines.append('%064x' % ((w >> (256 * seg)) & ((1 << 256) - 1)))
            lines.append('%064x' % mt)
        (a.out / f'coll_d{d}.hex').write_text('\n'.join(lines) + '\n')
        ncal = max(c['cal']) + 2
        assert ncal <= 1024, ncal
        (a.out / f'cal_d{d}.hex').write_text(''.join('%047x\n' % c['cal'].get(w, 0) for w in range(ncal)))
        nsec = SB + (P + 3) // 4 + 2
        vm = [[0] * nsec for _ in range(8)]
        for f in range(P):
            p = f % 4; v = vec(xs[d][f])
            vm[2 * p][SB + f // 4] = v & ((1 << 256) - 1); vm[2 * p + 1][SB + f // 4] = v >> 256
        (a.out / f'vm_d{d}.hex').write_text(''.join('%064x\n' % vm[b][s] for b in range(8) for s in range(nsec)))
        peer = 1 - d
        rxe = [(meta33(peer, f % 4) << 512) | vec(xs[peer][f]) for f in range(P)]
        (a.out / f'rx_d{d}.hex').write_text(''.join('%0137x\n' % x for x in rxe))
        if a.kind == 'ag':
            pubs = rxe
        else:
            pubs = [(meta33(d, f if a.ar_iter else f % 8) << 512) | vec([f32(x + y) for x, y in zip(xs[d][f], xs[peer][f])]) for f in range(P)]
        (a.out / f'pub_d{d}.hex').write_text(''.join('%0137x\n' % x for x in pubs))
        (a.out / f'adr_d{d}.hex').write_text(''.join('%010x\n' % (DB + 64 * f) for f in range(P)))
        plan[d] = dict(C=C, ready_assumed=ready, release_word=c['rel_w'], guard=a.guard, rows=len(words), unrolled=c['end'] + 1,
                       cal_words=ncal, nsec=nsec, first_vm_row=c['tx'][0]['vm'], first_wr_row=c['tx'][0]['wr'],
                       tx=[(t['vm'], t['wr'], t['rd']) for t in c['tx']], rx=c['rx'], pub_rows=c['pub'],
                       loops=[(row['u'], row['T'], row['n'], row['step']) for row in rows if row['T'] > 1 and row['u'] == rows[row['body_start']]['u']])
    if a.kind == 'rs':
        dif = sum(1 for f in range(P) for l in range(16)
                  if bits(f32(xs[0][f][l] + xs[1][f][l])) != bits(xs[0][f][l]) )
        assert dif > 0
    info = dict(kind=a.kind, frames=P, plan=plan, mut=a.mut, release_early=a.release_early)
    (a.out / 'plan.json').write_text(json.dumps(info, indent=1) + '\n')
    print('XDIE2_PLANINFO ' + json.dumps({d: dict(rows=plan[d]['rows'], cal=plan[d]['cal_words'], rel=plan[d]['release_word'],
                                                 K1=plan[d]['C']['K1'], K2=plan[d]['C']['K2'], gcL=plan[d]['C']['gcL'],
                                                 loops=plan[d]['loops']) for d in (0, 1)}))
    print(f"XDIE3_FIRSTWR {plan[0]['first_wr_row']} {plan[1]['first_wr_row']}")
    print(f"XDIE2_ARGS +NR0={plan[0]['rows']} +NR1={plan[1]['rows']} +NC0={plan[0]['cal_words']} +NC1={plan[1]['cal_words']} "
          f"+NSEC={plan[0]['nsec']} +NF={P} +NPUB={P}")


if __name__ == '__main__':
    main()
