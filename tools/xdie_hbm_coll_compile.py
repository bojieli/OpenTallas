#!/usr/bin/env python3
"""TOKEN-XDIE-HBM2 (2026-10-18): compiler for the two-die HBM d4g GEN2 cross-die ALL_REDUCE co-sim
(rtl/hbm_accel/generic/collective/xdie/tb_xdie_hbm_coll.sv).

Lowers one cross-die AR step (2 dies x 2 local FP32 vectors of 16 lanes, golden rank-order fold ((x0+x1)+x2)+x3 on BOTH
dies) to the actual programmes of the real die elements, at compiler cycles:
  * hb_coll_NE (ot_hfd_coll_q2_hard_v8g, NLINK 1): F20 rows of the v4/v5 1536-b ISA (rtl/.../p2p/static_uop_layout_v4.json),
    with self-loop rows for idle runs (static_issuer_v6 metadata {next, target, count, halt, lid}, <= 64 rows);
  * epcal_NE (hfd_hgi_vm_calendar, 187-b universal words; ep_N2 RX controls = word[18:0]): arm / release / drain slots.
Pattern: tools/hbm_coll_static/allgather.py (unrolled schedule -> rows, independent unroll check) on layout v4.

Timing contract used (row-relative, from the native benches; u = unrolled issue cycle of the die's programme):
  SU request u -> qslots capture u+12 (INJLAT 12) -> sink instruction u+13 -> consumer (reduce op / link wr) u+15;
  link wr/rd/rx sequence fields one row BEFORE the reservation (ctl_v5 registers them; layout v4 note);
  rd >= wr + 8 (link_e store write -> read), rd TX beat valid: pre-edge gearbox state (L + K1 + u_rd + 18) not phase 4 /
  not IDLE (hfd_ep_static TX calendar; xdie_hbm_1018 LTX = 8 + RLY);  rx_expect at the edge the RX pin is sampled =
  ep slot sample + 16 (DRX, xdie_hbm_1018); RX capture rx_expect+3, sink +4, op +6;  reduce: load / add_read at R,
  add_issue R+1, writeback R+9 (next dependent read), publication read >= last issue + 9, pub_issue +1, reduce-source
  capture +1, delivery sink +1.
Die constants measured by the co-sim itself (stage logs): K1 = launch edge -> link samples row u at L+K1+u;
K2 = launch -> ep samples calendar word w at L+K2+w; gcL = TX gearbox group counter at L (pre-edge phase 0 by the host
launch protocol); READY = edge (rel. L) at which the peer block is ready at this die's ep.  Static release word =
READY + GUARD - K2 (GUARD 8 cycles: ready max + 8, as xdie_hbm_1018 LXB).  Nothing waits on a ready signal on-die.

  xdie_hbm_coll_compile.py OUT --from LOG|- [--guard G] [--release-early N] [--mut order|flip]
  xdie_hbm_coll_compile.py measure LOG          (prints the measured constants as JSON)
"""
import argparse, json, pathlib, random, re, struct, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'hbm_static'))
import leaf_split_latency as LS  # noqa: E402  HBM-P6-CMP over-cap leaf-split shifts
# reduce-source publication offset: 0 on the pinned ot_hgi_coll_reduce_static; LS 'coll_reduce_pub' (+1) on the
# over-cap split parent ot_hfd_coll_q2_hard_v8g_s (u_reduce = ot_hgi_coll_reduce_static_pr: input pin registers, the
# reduce runs 1 edge later; operands and controls enter through the same registers, so only the publication moves).
RED_PUB = 0
NPT, ND = 1, 14
SRC_SU0, SRC_RAIL0, SRC_RED = 0, 2, NPT + 6          # source order SU0,SU1,rail0,VM0..3,reduce
DST_RAIL0, DST_DEL0, DST_RED = 0, NPT, ND - 1        # sink order rail0,SU0..3,RGX0..3,TKM0..3,reduce
IDLE_K = 204
INJ_CAP, RX_CAP = 12, 3
EPOCH = 0x3a
F = dict(capture_slot=(0, 10), sink_slot=(10, 16), sink_select=(26, 64), inj_rd=(90, 2), inj_idx=(92, 32),
         inj_meta=(284, 66), lk_wr_v=(350, 3), lk_wr_slot=(353, 18), lk_rd_v=(371, 3), lk_rd_slot=(374, 18),
         lk_rx_expect=(392, 3), lk_rx_slot=(395, 18), lk_epoch_begin=(413, 3), lk_epoch=(416, 8), del_obase=(874, 160),
         lk_wr_seq_high=(1415, 30), lk_rd_seq_high=(1445, 30), lk_rx_seq_high=(1475, 30))
AR = dict(load_v=(0, 1), load_tag=(1, 4), add_read=(5, 1), read_tag=(6, 4), add_issue=(10, 1), pub_read=(11, 1),
          pub_tag_a=(12, 4), pub_release=(21, 1), pub_issue=(22, 1), pub_src=(23, 8), pub_index=(31, 16))


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


def fadd(a, b):  # binary32 RNE: exact double sum of two binary32 (exponent spread < 29) rounded once
    return f32(a + b)


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def operands(seed=1018):
    r = random.Random(seed)
    xs = []
    for k in range(4):
        lanes = []
        for l in range(16):
            e = r.randint(-9, 9)
            m = 1.0 + r.getrandbits(23) / float(1 << 23)
            lanes.append(f32(r.choice((1.0, -1.0)) * m * 2.0 ** e))
        xs.append(lanes)
    return xs


def fold(xs, order):
    out = []
    for l in range(16):
        acc = xs[order[0]][l]
        for k in order[1:]:
            acc = fadd(acc, xs[k][l])
        out.append(acc)
    return out


def vec(lanes):
    return sum(bits(v) << (32 * l) for l, v in enumerate(lanes))


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


class Prog:
    def __init__(self):
        self.rows = {}
        self.ar = {}

    def set(self, u, k, v, j=0):
        lsb, w = F[k]
        r = self.rows.setdefault(u, {})
        r[k] = r.get(k, 0) | (v << j)

    def a(self, u, **kv):
        r = self.ar.setdefault(u, {})
        for k, v in kv.items():
            assert k not in r, (u, k)
            r[k] = v

    def word(self, u):
        w = 0
        for k, v in self.rows.get(u, {}).items():
            lsb, wd = F[k]
            assert 0 <= v < (1 << wd), (u, k, v)
            w |= v << lsb
        if u in self.ar:
            a = 0
            for k, v in self.ar[u].items():
                lsb, wd = AR[k]
                assert 0 <= v < (1 << wd), (u, k, v)
                a |= v << lsb
            w |= (a & ((1 << 31) - 1)) << 1505
            w |= (a >> 31) << 688
        return w


def compile_die(d, C, order, rel_w, gap, early=0):
    """d: die, C: constants {K1,K2,gcL}, order: fold order (operand ids), rel_w: release calendar word."""
    P = Prog()
    K1, K2, gcl = C['K1'], C['K2'], C['gcL']
    loc = [2 * d, 2 * d + 1]
    P.set(0, 'lk_epoch_begin', 1); P.set(0, 'lk_epoch', EPOCH)
    used_inj = set()

    def inject(u_op, k, dests):
        u = u_op - 15
        assert u >= 1 and u not in used_inj, ('inject', d, u, k)
        used_inj.add(u)
        P.set(u, 'inj_rd', 1); P.set(u, 'inj_idx', k)
        P.set(u, 'inj_meta', (1 << 32) | (0xff << 24) | (d << 16) | k)
        P.set(u + INJ_CAP, 'capture_slot', 1 << SRC_SU0)
        for dst in dests:
            P.set(u + 13, 'sink_slot', 1 << dst); P.set(u + 13, 'sink_select', SRC_SU0 << (4 * dst))

    def seq(u, kind, s):   # sequence fields one row before the reservation
        P.set(u - 1, 'lk_%s_slot' % kind, s & 63); P.set(u - 1, 'lk_%s_seq_high' % kind, s >> 6)

    # ---- TX: the two local vectors, frames seq 0, 1 (wr at 17, 18; rd on the first valid TX beats >= wr + 8)
    WR = [17, 18]
    tx_reduce = {}
    for f, k in enumerate(loc):
        tx_reduce[k] = WR[f]
    rd, u = [], WR[0] + 8
    while len(rd) < 2:
        if beat_ok(K1 + u + 18, gcl) and u >= WR[len(rd)] + 8:
            rd.append(u)
        u += 1
    # ---- calendar (RX of the peer's two frames): arm word 0, static release rel_w, drain slots chosen below
    cal = {0: (1 << 0) | (0 << 1) | (2 << 2)}           # arm bank 0, 2 words
    rel_w = rel_w - early
    cal[rel_w] = cal.get(rel_w, 0) | (1 << 9)          # release bank 0
    # remote operand f (frame f of the peer = operand 2*(1-d)+f): op time = K2 + w_slot + 16 - K1 + 6
    def op_of_slot(w):
        return K2 + w + 16 - K1 + 6
    # ---- golden fold schedule (left fold in `order`; dependent read >= previous issue + 9)
    t_prev_issue = None
    slots = []
    ops = []
    for j, k in enumerate(order):
        lo = 0 if t_prev_issue is None else t_prev_issue + 9
        if k in loc:
            t = max(lo, tx_reduce[k] if k in tx_reduce else 0)
            if k in tx_reduce and t == tx_reduce[k]:
                pass                                   # same inject as its TX frame (sink to rail + reduce)
            else:
                t = max(t, 17)
                while (t - 15) in used_inj or any(t == WR[f] for f in range(2)):
                    t += 1
                inject(t, k, [DST_RED])
                tx_reduce.pop(k, None)
        else:
            f = k - 2 * (1 - d)
            w = rel_w + 1 if not slots else slots[-1] + 1
            while op_of_slot(w) < lo:
                w += 1
            slots.append(w)
            t = op_of_slot(w)
        if j == 0:
            P.a(t, load_v=1, load_tag=0)
        else:
            P.a(t, add_read=1, read_tag=0); P.a(t + 1, add_issue=1); t_prev_issue = t + 1
        ops.append((k, t))
    # the TX injects (rail sink; + reduce sink when the fold consumes that vector at its TX time)
    for f, k in enumerate(loc):
        dests = [DST_RAIL0] + ([DST_RED] if any(kk == k and tt == WR[f] for kk, tt in ops) else [])
        inject(WR[f], k, dests)
        P.set(WR[f], 'lk_wr_v', 1); seq(WR[f], 'wr', f)
        P.set(rd[f], 'lk_rd_v', 1); seq(rd[f], 'rd', f)
    # remote frames: drain slot f at word slots[f] -> rx_expect at the RX pin sample edge, capture +3, sink +4
    assert len(slots) == 2 and slots[0] > rel_w and slots[1] > slots[0], slots
    rx = []
    for f, w in enumerate(slots):
        cal[w] = cal.get(w, 0) | (1 << 11) | (0 << 12) | (f << 13)
        ux = K2 + w + 16 - K1
        rx.append(ux)
        P.set(ux, 'lk_rx_expect', 1); seq(ux, 'rx', f)
        P.set(ux + RX_CAP, 'capture_slot', 1 << SRC_RAIL0)
        P.set(ux + RX_CAP + 1, 'sink_slot', 1 << DST_RED); P.set(ux + RX_CAP + 1, 'sink_select', SRC_RAIL0 << (4 * DST_RED))
    # ---- publication (FP32, tag 0, release) -> reduce source -> delivery 0
    tp = t_prev_issue + 9
    R = RED_PUB
    P.a(tp, pub_read=1, pub_tag_a=0, pub_release=1, pub_src=d, pub_index=0xA5)
    P.a(tp + 1, pub_issue=1)
    P.set(tp + 2 + R, 'capture_slot', 1 << SRC_RED)
    P.set(tp + 3 + R, 'sink_slot', 1 << DST_DEL0); P.set(tp + 3 + R, 'sink_select', SRC_RED << (4 * DST_DEL0))
    P.set(tp + 3 + R, 'del_obase', 0x10000 + 3 * 0x4000)
    end = tp + 6 + R
    return dict(P=P, end=end, rd=rd, wr=WR, rx=rx, slots=slots, rel_w=rel_w, ops=ops, cal=cal, pub=tp + 3 + R)


def lower(P, end):
    """unrolled words 0..end -> issuer rows (self-loop rows for runs of identical words); independent unroll check."""
    words = [P.word(u) for u in range(end + 1)]
    rows, meta, rowof = [], [], {}
    u = 0
    while u <= end:
        n = 1
        while u + n <= end and words[u + n] == words[u] and u + n < end:
            n += 1
        r = len(rows)
        m = (r + 1) & 63
        if n > 1:
            m |= (r << 6) | (n << 12) | (r << 45)
        rows.append(words[u]); meta.append(m)
        for i in range(n):
            rowof[u + i] = r
        u += n
    meta[-1] |= 1 << 44
    assert len(rows) <= 64, ('programme capacity', len(rows))
    # unroll the actual metadata/counter ISA (ot_hgi_coll_static_issuer_v6 semantics) and compare word by word
    pc, cnt, out = 0, [0] * 64, []
    for _ in range(10 * (end + 2)):
        m = meta[pc]; out.append(rows[pc])
        if m >> 44 & 1:
            break
        count, lid = (m >> 12) & 0xffffffff, (m >> 45) & 63
        if count and cnt[lid] < count - 1:
            cnt[lid] += 1; pc = (m >> 6) & 63
        else:
            if count:
                cnt[lid] = 0
            pc = m & 63
    assert out == words, 'unroll mismatch'
    lower.rowof = rowof
    return rows, meta


def measure(log):
    """per die: K1, K2, gcL, READY (rel L), K3 (slot -> rx pin), TX beat states, PASS/FAIL."""
    txt = pathlib.Path(log).read_text() if log != '-' else ''
    M = {0: {}, 1: {}}
    plan = None
    for line in txt.splitlines():
        m = re.match(r'XDIE2_PLANINFO (.*)', line)
        if m:
            plan = json.loads(m.group(1))
    for d in (0, 1):
        g = lambda pat: [tuple(int(x) for x in ((mm,) if isinstance(mm, str) else mm)) for mm in re.findall(pat % d, txt)]
        L = g(r'XDIE2_L d=%d edge=(\d+) ph=(\d+) gc=(\d+)')
        if L:
            M[d]['gcL'] = L[0][2]
        wr = g(r'XDIE2_WR d=%d rel=(-?\d+)')
        arm = g(r'XDIE2_ARM d=%d rel=(-?\d+) bank')
        rdy = g(r'XDIE2_RDY d=%d bank=0 rel=(-?\d+)')
        slot = g(r'XDIE2_SLOT d=%d rel=(-?\d+) ')
        pin = g(r'XDIE2_RXPIN d=%d rel=(-?\d+)')
        if wr:
            M[d]['WR_rel'] = wr[0][0]
        if arm:
            M[d]['K2'] = arm[0][0]
        if rdy:
            M[d]['READY'] = rdy[0][0]
        if slot and pin:
            M[d]['K3'] = [p[0] - s[0] for s, p in zip(slot, pin)]
    M['pass'] = bool(re.search(r'^XDIE2 .* PASS$', txt, re.M))
    return M


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'measure':
        print(json.dumps(measure(sys.argv[2]))); return
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('--from', dest='frm', default='-', help='previous stage log (measured constants) or -')
    ap.add_argument('--k1', type=int, default=11); ap.add_argument('--k2', type=int, default=7)
    ap.add_argument('--ready', type=int, default=520, help='assumed READY (rel L) when not measured')
    ap.add_argument('--guard', type=int, default=8)
    ap.add_argument('--release-early', type=int, default=0)
    ap.add_argument('--mut', default='', choices=['', 'order', 'flip'])
    ap.add_argument('--leaf-split', type=int, default=None,
                    help='1: hb_coll = over-cap split ot_hfd_coll_q2_hard_v8g_s (reduce publication +1); default '
                         'OT_HBM_LEAF_SPLIT (0 = pinned v8g)')
    a = ap.parse_args()
    global RED_PUB
    RED_PUB = LS.shift('coll_reduce_pub', None if a.leaf_split is None else bool(a.leaf_split))
    print(f'XDIE2_LEAF_SPLIT red_pub={RED_PUB}')
    check_layout()
    a.out.mkdir(parents=True, exist_ok=True)
    M = measure(a.frm) if a.frm != '-' else {0: {}, 1: {}}
    xs = operands()
    gold = fold(xs, [0, 1, 2, 3])
    swap = fold(xs, [2, 3, 0, 1])
    ndiff = sum(bits(x) != bits(y) for x, y in zip(gold, swap))
    assert ndiff >= 4, ('operands do not make the fold order observable', ndiff)
    assert all(abs(v) > 1e-30 for v in gold)
    plan = {}
    for d in (0, 1):
        m = M[d]
        C = dict(K1=(m['WR_rel'] - 17) if 'WR_rel' in m else a.k1, K2=m.get('K2', a.k2), gcL=m.get('gcL', 0))
        ready = m.get('READY', a.ready)
        rel_w = ready + a.guard - C['K2']
        order = [0, 1, 2, 3]
        if a.mut == 'order' and d == 1:
            order = [2, 3, 0, 1]
        c = compile_die(d, C, order, rel_w, 10, early=a.release_early if d == 1 else 0)
        rows, meta = lower(c['P'], c['end'])
        if a.mut == 'flip' and d == 1:     # programme word flip: die 1's second rx_expect row loses its reservation bit
            r = lower.rowof[c['rx'][1]]
            assert rows[r] >> F['lk_rx_expect'][0] & 1 and (meta[r] >> 12) & 0xffffffff == 0, r
            rows[r] ^= 1 << F['lk_rx_expect'][0]
        lines = []
        for w, mt in zip(rows, meta):
            for seg in range(6):
                lines.append('%064x' % ((w >> (256 * seg)) & ((1 << 256) - 1)))
            lines.append('%064x' % mt)
        (a.out / f'coll_d{d}.hex').write_text('\n'.join(lines) + '\n')
        ncal = max(c['cal']) + 2
        assert ncal <= 1024, ncal
        (a.out / f'cal_d{d}.hex').write_text(''.join('%047x\n' % c['cal'].get(w, 0) for w in range(ncal)))
        su = [0] * 16
        for k in (2 * d, 2 * d + 1):
            su[k] = vec(xs[k])
        (a.out / f'su_d{d}.hex').write_text(''.join('%0128x\n' % v for v in su))
        plan[d] = dict(C=C, ready_assumed=ready, release_word=c['rel_w'], guard=a.guard, order=order, rows=len(rows),
                       unrolled=c['end'] + 1, cal_words=ncal, wr=c['wr'], rd=c['rd'], rx_expect=c['rx'],
                       drain_slots=c['slots'], ops=c['ops'], publication_row=c['pub'])
    (a.out / 'xk.hex').write_text(''.join('%0128x\n' % vec(x) for x in xs))
    (a.out / 'golden.hex').write_text(''.join('%0137x\n' % (((1 << 32) | (0xff << 24) | (d << 16) | 0xA5) << 512 | vec(gold))
                                              for d in (0, 1)))
    info = dict(plan=plan, mut=a.mut, release_early=a.release_early, golden_order=[0, 1, 2, 3], order_sensitive_lanes=ndiff,
                golden_hex=['%08x' % bits(v) for v in gold])
    (a.out / 'plan.json').write_text(json.dumps(info, indent=1) + '\n')
    print('XDIE2_PLANINFO ' + json.dumps({d: dict(rows=plan[d]['rows'], cal=plan[d]['cal_words'], rel=plan[d]['release_word'],
                                                 K1=plan[d]['C']['K1'], K2=plan[d]['C']['K2'], gcL=plan[d]['C']['gcL'])
                                         for d in (0, 1)}))
    print(f"XDIE2_ARGS +NR0={plan[0]['rows']} +NR1={plan[1]['rows']} +NC0={plan[0]['cal_words']} +NC1={plan[1]['cal_words']}")


if __name__ == '__main__':
    main()
