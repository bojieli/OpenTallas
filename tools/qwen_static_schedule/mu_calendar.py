"""MU-QWEN 2026-10-18 (owner MU.DECIDE option A): the Qwen3-8B ROM 4-user static calendar.

Static schedule only (owner 0ah): every user's work is a RIGID copy of the single-user layer programme (the same
windows at the same offsets from its layer start, so its internal cycle schedule and its exactness are the single-user
ones); the compiler only chooses each copy's start cycle.  A collision is a compile error here and a sticky fault in
the RTL, never a stall.

Construction (results/arch/rom_multiuser_1018/README.md sections 1, 3, 4 on claude/rom-multiuser-1018):
  * user 0 = the latency user: its timeline is the compiled single-user timeline, bit-for-bit (layer blocks back to back,
    then its LM head and its embedding hand-off, then the next token).  It is placed FIRST and never moved.
  * users 1..NU-1 = fillers: user k's first layer block is placed at the earliest start >= round(k * P / NU) whose
    windows collide with nothing already placed; every later block (layer l+1 after layer l, the head after layer 35,
    the next token's layer 0 after its embedding) at the earliest start >= the end of the previous block.  The gap a
    filler waits (mostly around every user's 3,048-cycle LM head, which is longer than a slot) is its static bubble.
  * the SHIFT LEMMA (README section 3) is asserted twice: (a) on the layer frame, every resource's windows of the
    reference block are disjoint from the same windows shifted by every user-pair difference of the chosen first starts
    (mod the layer period); (b) on the whole emitted schedule, every resource's windows over all users and all tokens
    are pairwise disjoint (independent of how the scheduler chose them), and user 0's windows equal the single-user ones.

Resources (one entry per physical unit that serves one user at a time):
  me       compute-die ROM tile field (qkv, o_proj, gate_up, down; the LM head)
  su       compute-die stream unit / VM vector work (rmsnorm1, qknorm_rope, rmsnorm2, residual busy part; head epilogue)
  kvs      KV-die attention service (one instance; its HBM PC command streams run inside this window)
  d2d_q    compute -> KV q record lane;  d2d_o  KV -> compute attention result lane
  coll.*   the TP8 collective engine (ot_coll_tp8_static) at WORD level: issue slots (slot sequencer), pairing B, S-ring /
           SerDes write W, output O, gather hold, and the shared UCIe P/R frames, from tools/qwen_coll_tp8_static_bench.
           word_events at the implemented LU / LS (the engine's own resources; overlapping epochs are legal when these
           sets are disjoint -- the engine is a fixed-offset pipeline, its sequencer is busy `words` cycles a command)
  host     KV-die host plane next-token return (133.5 cycles a token per user, off the critical path)
Every timing input names its source; a missing input refuses the compile (ScheduleError).
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

from .calendar import ScheduleError

ROOT = Path(__file__).resolve().parents[2]


def _mod(rel, name):
    s = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


# ---- sourced constants -------------------------------------------------------------------------------------------
# Production layer programme of record (results/rtl/qwen_layer_tput_1013/record.json windows[].price_production; the
# TP8 all-reduce windows 1,121 / 979 are the xdie_qtp8_1018 prices; KV-die attention 1,816 its own record).
LAYER_WINDOWS = (            # (op, unit, latency cycles = production price, unit-busy cycles = measured window)
    ("rmsnorm1", "su", 15, 1), ("qkv", "me", 259, 167), ("qknorm_rope", "su", 101, 94), ("attention", "kv", 1816, None),
    ("o_proj", "me", 382, 283), ("allreduce1", "coll", 1121, None), ("attn_tail", "su", 2, 2), ("rmsnorm2", "su", 91, 91),
    ("gate_up", "me", 632, 544), ("down", "me", 370, 289), ("allreduce2", "coll", 979, None), ("residual", "su", 1067, 265))
SRC_LAYER = ("results/rtl/qwen_layer_tput_1013/record.json windows[]: latency = price_production (sum 6,835 = "
             "production_layer.priced), unit busy = measured window (me class 1,283, su class 462; rmsnorm2 capped at "
             "its price); the production adders (die relays 430 um, issue relays, stations) are latency, not occupancy; "
             "the busy part sits centred in its window (modelled placement)")
SOURCED = dict(
    layer_period=6886,           # composed per-layer cycles (rom_multiuser_1018 LP = 4,640 + 2,246, token_path_1018)
    l0_extra=399,                # token_path_1018 L0 die 5,039 - Lc die 4,640 (L0 cold KV fill), on the compute die
    head_cycles=3048,            # measured-old-RTL LM head on the tile field (qwen_layer_tput_1013 head.measured)
    embed_cycles=272,            # token_path_1018 embed xdie (priced): KV-die embedding row -> compute die
    kv_service=1555,             # measured-old-RTL KV-die static attention service (qwen_attention_rate_1015)
    d2d_record=32,               # 2 KB a KV die a layer over a 512-b lane (s81_balance_1018 section 2, modelled)
    host_return=134,             # 133.5 cycles a token per user (rom_multiuser_1018 item 6)
    ar_words=256,                # 4,096 FP32 = 256 x 512-b words an all-reduce (TP8 production shape)
    lu=53, ls=378,               # implemented UCIe / SerDes collective latencies (dv2f14bi calendar LS 378, qcollcal3_1018)
    users=4,
)
REQUIRED = tuple(SOURCED)   # optional: occupancy="priced" (unit busy = the whole priced window; sensitivity)

TP8 = _mod("tools/qwen_coll_tp8_static_bench.py", "qwen_coll_tp8_static_bench_mu")


def _need(p):
    miss = [k for k in REQUIRED if k not in p]
    if miss:
        raise ScheduleError(f"MU calendar inputs missing: {miss}")
    if p["users"] < 1:
        raise ScheduleError("users >= 1")
    return p


# ---- the rigid blocks ----------------------------------------------------------------------------------------------
def coll_sets(c, p, mode=0, words=None):
    """engine resource cycles of one collective message whose command reaches the engine at cycle c"""
    n = words or p["ar_words"]
    slots, b, wr, out, hold = TP8.word_events(mode, c, n, p["lu"], p["ls"])
    pev = [x + 2 for x in slots]                               # UCIe P frame (A + 1)
    rev = [x - p["lu"] - 2 for x in out] if mode == 0 else []  # UCIe R frame (reduce only)
    return {"coll.issue": _runs(slots), "coll.B": _runs(b), "coll.W": _runs(wr), "coll.O": _runs(out),
            "coll.hold": _runs(hold), "coll.ucie": _runs(pev + rev)}


def _runs(cycles):
    """unit-cycle events -> maximal runs [a, b); a repeated cycle (double booking inside one message) refuses"""
    xs = sorted(cycles)
    if len(set(xs)) != len(xs):
        raise ScheduleError("one message books a resource cycle twice")
    out = []
    for x in xs:
        if out and out[-1][1] == x:
            out[-1][1] = x + 1
        else:
            out.append([x, x + 1])
    return [tuple(r) for r in out]


def layer_block(p, l0=False):
    """windows of one layer of one user, offsets from its layer start: {resource: [(a, b)]}, and the block length"""
    w, t, ops = {}, 0, {}
    extra = p["l0_extra"] if l0 else 0

    def add(r, a, b):
        w.setdefault(r, []).append((a, b))
    for op, unit, n, busy in LAYER_WINDOWS:
        if op == "qkv":
            n += extra                                             # L0 cold KV fill rides the compute-die front
            busy += extra
        n0 = n
        if unit == "kv":                                           # MU-D2D-OVL 10-19 (opt-in, default 0): the RTL
            n += p.get("attn_extra", 0)                            # exchange is longer than the priced window
        ops[op] = (t, t + n)
        if unit in ("me", "su"):
            bz = n if p.get("occupancy") == "priced" else min(busy, n)
            a0 = t + (n - bz) // 2
            add(unit, a0, a0 + bz)
        elif unit == "kv":
            lat = (n0 - p["kv_service"] - 2 * p["d2d_record"]) // 2  # D2D flight each way (modelled split)
            add("d2d_q", t, t + p["d2d_record"])
            s0 = t + p["d2d_record"] + lat
            add("kvs", s0, s0 + p["kv_service"])
            add("d2d_o", t + n0 - p["d2d_record"], t + n0)
            # MU-D2D-OVL 10-19 (opt-in): the RTL link playheads of this exchange (d2d.ctx / d2d.crx / d2d.ktx / d2d.krx,
            # tools/qwen_static_schedule/mu_d2d_ovl.py), offsets from the attention op start (= the CMD send edge), so
            # they follow the op in L0 (l0_extra) as in L1..L35
            for r, iv in p.get("att_windows", {}).items():
                for a, b in iv:
                    add(r, t + a, t + b)
        elif unit == "coll":
            for r, iv in coll_sets(t, p).items():                  # the command reaches the engine at the window start
                for a, b in iv:
                    add(r, a, b)
        t += n
    for r, iv in p.get("seg_windows", {}).get("layer", {}).items():    # opt-in (MU-ADOPT-TOK): command-plane edges
        for a, b in iv:                                                # of the RTL layer segment (cmd / done / start)
            add(r, a, b)
    w = {r: v for r, v in w.items() if not any(r.startswith(d) for d in p.get("drop_resources", ()))}
    period = p["layer_period"] + extra
    if t > period:
        raise ScheduleError(f"layer programme {t} longer than the layer period {period}")
    return dict(windows=w, length=period, ops=ops, programme_cycles=t)


def head_blocks(p):
    """LM head on the tile field (+ SU epilogue) in head_chunks equal row chunks (a filler's head must fit the latency
    user's tile-field gaps, which are all shorter than 3,048; chunks merge the per-die running argmax in row order with
    the strict-greater rule, so the result is the single-shot head's), then the next token's embedding hand-off and the
    host return.  head_chunks 1 = the head as one 3,048-cycle window (single-user form)."""
    n = p.get("head_chunks", 1)
    h, e = p["head_cycles"], p["embed_cycles"]
    cuts = [h * i // n for i in range(n + 1)]
    sw, drop = p.get("seg_windows", {}), tuple(p.get("drop_resources", ()))

    def fin(w, kind):                                                  # opt-in extras / drops (MU-ADOPT-TOK)
        w = dict(w, **{r: list(iv) for r, iv in sw.get(kind, {}).items()})
        return {r: v for r, v in w.items() if not any(r.startswith(d) for d in drop)}
    out = [(f"head.c{i}", dict(windows=fin({"me": [(0, cuts[i + 1] - cuts[i])], "su": [(0, cuts[i + 1] - cuts[i])]},
                                           "head.c"), length=cuts[i + 1] - cuts[i])) for i in range(n)]
    # tok_ofs (MU-OPCAL-EMB 10-19, default 0 = unchanged): the edge, from the token-start block's start, at which the new
    # token is in the per-user token bank (mu_opcal.EMB_T); the embedding request / host return consume that token, so the
    # priced embedding window (d2d_o, host, the embed_cycles fetch) starts there and the block grows by it
    o = p.get("head_tok_ofs", 0)
    out.append(("head", dict(windows=fin({"d2d_o": [(o, o + p["d2d_record"])], "host": [(o, o + p["host_return"])]},
                                         "head"), length=o + e)))
    return out


def layer_ops(p, l0=False):
    """the layer split into its programme ops: [(op, {resource: [(a, b)]} relative to the op start, op length)].
    The last op absorbs the layer slack (period - programme), so op lengths sum to the layer period."""
    blk = layer_block(p, l0)
    out = []
    names = [o for o, _, _, _ in LAYER_WINDOWS]
    for i, op in enumerate(names):
        a, b = blk["ops"][op]
        end = blk["length"] if i == len(names) - 1 else b
        w = {}
        for res, iv in blk["windows"].items():
            for x, y in iv:
                if a <= x < b or (x == y == a):
                    w.setdefault(res, []).append((x - a, y - a))
        out.append((op, w, end - a))
    return out


def token_blocks(p, layers=36, granularity="layer"):
    """one token of one user as placement units: whole layers (granularity 'layer': today's per-stage starts, every
    layer rigid) or programme ops (granularity 'op': the sequencer interleaves users at op level)"""
    seq = []
    for i in range(layers):
        lname = f"L{i}"
        if granularity == "layer":
            seq.append((lname, layer_block(p, l0=(i == 0))))
        else:
            for op, w, n in layer_ops(p, l0=(i == 0)):
                seq.append((f"{lname}.{op}", dict(windows=w, length=n)))
    seq.extend(head_blocks(p))
    return seq


def single_user_period(p, layers=36):
    return sum(b["length"] for _, b in token_blocks(p, layers))


# ---- interval bookkeeping -----------------------------------------------------------------------------------------
class Reservations:
    def __init__(self):
        self.r = {}

    def collides(self, wins, t0):
        for res, iv in wins.items():
            have = self.r.get(res)
            if not have:
                continue
            for a, b in iv:
                A, B = a + t0, b + t0
                # have is a sorted list of disjoint intervals
                lo, hi = 0, len(have)
                while lo < hi:
                    m = (lo + hi) // 2
                    if have[m][1] <= A:
                        lo = m + 1
                    else:
                        hi = m
                if lo < len(have) and have[lo][0] < B:
                    return (res, A, B, have[lo])
        return None

    def add(self, wins, t0, owner):
        import bisect
        for res, iv in wins.items():
            lst = self.r.setdefault(res, [])
            for a, b in iv:
                bisect.insort(lst, (a + t0, b + t0, owner))

    def earliest(self, wins, t):
        while True:
            c = self.collides(wins, t)
            if c is None:
                return t
            res, A, B, h = c
            t += max(1, h[1] - A)                                  # jump past the blocking interval


def lemma_frame(p, starts):
    """shift lemma on the layer frame: the reference layer block's windows vs the same windows shifted by every user
    pair's start difference, mod the layer period (wrap-around included)"""
    blk = layer_block(p)
    P = p["layer_period"]
    bad = []
    for i, si in enumerate(starts):
        for j, sj in enumerate(starts):
            if j <= i:
                continue
            d = (sj - si) % P
            for res, iv in blk["windows"].items():
                for a, b in iv:
                    for a2, b2 in iv:
                        for k in (-1, 0, 1):
                            A2, B2 = a2 + d + k * P, b2 + d + k * P
                            if a < B2 and A2 < b:
                                bad.append(dict(users=(i, j), resource=res, window=(a, b), shifted=(A2, B2)))
    return bad


def cal_starts(sched):
    return {u: seq[0][1] for u, seq in sched.items()}


def lemma_frame_ops(starts, p):
    """op granularity: users are not pure shifts (each op may wait), so the frame lemma is replaced by the exact
    whole-schedule check (verify); report the frame-lemma violations of the pure-shift placement for reference"""
    return lemma_frame(p, [starts[u] for u in sorted(starts)])


def verify(sched, ref):
    """whole-schedule check, independent of the scheduler: pairwise-disjoint windows per resource; user 0 == ref"""
    per = {}
    for u, blocks in sched.items():
        for name, t0, blk in blocks:
            for res, iv in blk["windows"].items():
                for a, b in iv:
                    per.setdefault(res, []).append((a + t0, b + t0, u, name))
    clashes = []
    for res, lst in per.items():
        lst.sort()
        for x, y in zip(lst, lst[1:]):
            if y[0] < x[1]:
                clashes.append(dict(resource=res, a=x, b=y))
    ident = [(n, t) for n, t, _ in sched[0]] == [(n, t) for n, t, _ in ref]
    return clashes, ident


# ---- argmax root merge: one user's candidates at a time (MU-QW-AMIX 10-19, coordinator item 2) --------------------
# The DV root (qfd_dv_scalar2) merges the slices' LM-head argmax candidates of ONE token; the RTL now carries the user
# with each candidate and raises a sticky fault when a merge holds two users' candidates (MU_NU > 1).  The compiler side
# is this assertion: two users' root-merge windows never overlap.
AM_EMIT_T = 8          # the token-start ("head") block issues the previous token's AMAX emit at T = 8 (= mu_opcal)
AM_SLICES = 12         # DV slices on the scalar chain (W5 .. W0 E0 .. E5), commands enter at W5 = slice 0


def am_root_window(n_slices=AM_SLICES):
    """[lo, hi): the edges, relative to the edge the AMAX emit enters slice 0's command pin register (cmd_q), on which
    the root can merge a candidate of that emit -- worst case over the root position (ROOT cfg, any slice).
    Derivation from the RTL (rtl/qwen_dv/qfd_dv_slice2.sv, qfd_dv_scalar2.sv, mu/qfd_dv_amax_mu.sv):
      command chain    cmd_o <= cmd_q, next slice cmd_q <= cmd_i: 2 edges a hop -> slice k decodes the emit at e + 2k
                       (one broadcast AMAX, dst 15)
      slice argmax     c_am at cmd_q -> am_emit register (+1) -> am_v (comb.) -> the scalar out register dn_o / up_o
                       takes the AMI beat (+1), the AMV beat one edge later (am2 register, +1): AMV leaves at e + 2k + 3
      scalar chain     a hop = the neighbour's pin register scd_q / scu_q (+1) + its pass register dn_o / up_o (+1)
      root merge       the AMV beat in the root's pin register merges into am_best on the next edge (+1); the root's own
                       candidate (o_am) merges the edge after am_emit (e + 2r + 2)
      => a candidate of slice k reaches root r at  e + 2k + 2|k - r| + 3  (k != r),  the root's own at  e + 2r + 2.
    n = 12: root at W5 (r = 0): own at e + 2, slice 11 at e + 47 -> [2, 48); every other root position lies inside.
    Two users' emits e1 < e2 are legal iff [e1 + lo, e1 + hi) and [e2 + lo, e2 + hi) are disjoint (e2 - e1 >= 46).
    (mu_opcal.AM_ROOT_SPAN = 48 >= 46: its reserved window covers this one.)"""
    lo, hi = None, None
    for r in range(n_slices):
        arr = [2 * r + 2] + [2 * k + 2 * abs(k - r) + 3 for k in range(n_slices) if k != r]
        lo = min(arr) if lo is None else min(lo, min(arr))
        hi = max(arr) + 1 if hi is None else max(hi, max(arr) + 1)
    return lo, hi


def check_root_merge(sched, n_slices=AM_SLICES):
    """assert: no two users' argmax root-merge windows overlap.  Every user's token-start block ("head") emits at
    t0 + AM_EMIT_T and occupies the root on [emit + lo, emit + hi) (am_root_window).  Raises ScheduleError naming the
    users, the emit cycles and the window; returns the number of emits checked."""
    lo, hi = am_root_window(n_slices)
    iv = sorted((t0 + AM_EMIT_T + lo, t0 + AM_EMIT_T + hi, u, t0 + AM_EMIT_T)
                for u, blocks in sched.items() for name, t0, _ in blocks if name == "head")
    for i, (a, b, u, e) in enumerate(iv):
        for a2, b2, u2, e2 in iv[i + 1:]:
            if a2 >= b:
                break
            if u2 != u:
                raise ScheduleError(f"argmax root merge mixes users {u} and {u2}: emits at cycles {e} and {e2}, root "
                                    f"windows [{a}, {b}) and [{a2}, {b2}) overlap (window [{lo}, {hi}) after the emit)")
    return len(iv)


def compile_calendar(p=None, tokens=3, layers=36, eps_max=400, granularity="op", starts=None, policy="joint"):
    """emit the NU-user calendar over `tokens` reference tokens; raise ScheduleError on any collision"""
    p = _need(dict(SOURCED, **(p or {})))
    NU, P = p["users"], p["layer_period"]
    blocks = token_blocks(p, layers, granularity)
    T = single_user_period(p, layers)
    if sum(b["length"] for _, b in blocks) != T:
        raise ScheduleError("placement units do not tile the single-user token")
    # user 0: single-user timeline
    ref, t = [], 0
    for _ in range(tokens):
        for name, b in blocks:
            ref.append((name, t, b))
            t += b["length"]
    horizon = t
    R = Reservations()
    for name, t0, b in ref:
        R.add(b["windows"], t0, 0)
    sched = {0: list(ref)}
    first = [0]
    tok_done = {0: [t0 + b["length"] for name, t0, b in ref if name == "head"]}
    # fillers: joint list scheduling -- repeatedly place the filler unit that can start earliest (ties: lower user),
    # each unit at the earliest collision-free start >= its predecessor's end; user k's first unit >= round(k P / NU)
    nxt = {k: ((starts[k - 1] if starts else round(k * P / NU)), 0) for k in range(1, NU)}
    for k in range(1, NU):
        sched[k], tok_done[k] = [], []
    live = set(nxt)
    while live:
        cand = []
        for k in sorted(live):
            t, i = nxt[k]
            name, b = blocks[i % len(blocks)]
            cand.append((R.earliest(b["windows"], t), k, i, name, b))
        t, k, i, name, b = min(cand) if policy == "joint" else min(cand, key=lambda c: (c[1], c[0]))
        if t + b["length"] > horizon:
            live.discard(k)
            continue
        if not sched[k]:
            first.append(t)
        R.add(b["windows"], t, k)
        sched[k].append((name, t, b))
        if name == "head":
            tok_done[k].append(t + b["length"])
        nxt[k] = (t + b["length"], i + 1)
    first = [0] + [sched[k][0][1] if sched[k] else None for k in range(1, NU)]
    clashes, ident = verify(sched, ref)
    lemma = lemma_frame(p, [x for x in first if x is not None])
    if clashes:
        raise ScheduleError(f"calendar collision: {clashes[:3]}")
    if not ident:
        raise ScheduleError("latency user timeline differs from the single-user timeline")
    root_emits = check_root_merge(sched)
    # rates: steady-state token period per user = mean spacing of its token completions
    clk = 1.2e9
    users = []
    for u in range(NU):
        d = tok_done[u]
        per = (d[-1] - d[0]) / (len(d) - 1) if len(d) > 1 else ((d[0] - first[u]) if d else None)
        bubbles = sum(max(0, t1 - (t0 + b0["length"])) for (_, t0, b0), (_, t1, _) in zip(sched[u], sched[u][1:]))
        users.append(dict(user=u, first_layer_start=first[u], tokens_completed=len(d), token_period=per,
                          tok_s=(clk / per) if per else None, bubble_cycles_total=bubbles, blocks=len(sched[u])))
    agg = sum(x["tok_s"] for x in users if x["tok_s"])
    return dict(schema="opentallas.qwen.mu_calendar.v1", inputs=p, layer_source=SRC_LAYER, granularity=granularity, users=users,
                single_user_token_cycles=T, single_user_tok_s=clk / T, aggregate_tok_s=agg, horizon_cycles=horizon,
                lemma_frame_violations=lemma, schedule_collisions=0, latency_user_identical=True,
                root_merge=dict(window=am_root_window(), emits_checked=root_emits, mixed=0), schedule=sched)


# ---- per-user collective commands for the RTL bench ------------------------------------------------------------------
def coll_commands(cal, t_lo=None, t_hi=None):
    """every all-reduce command (cycle the command reaches the engine, user, layer, which) inside [t_lo, t_hi)"""
    out = []
    for u, seq in cal["schedule"].items():
        for name, t0, b in seq:
            if name == "head":
                continue
            if "ops" in b:
                hits = [(op, t0 + b["ops"][op][0]) for op in ("allreduce1", "allreduce2")]
            elif name.endswith((".allreduce1", ".allreduce2")):
                hits = [(name.split(".")[1], t0)]
            else:
                hits = []
            for op, c in hits:
                if (t_lo is None or c >= t_lo) and (t_hi is None or c < t_hi):
                    out.append(dict(cycle=c, user=u, layer=name.split(".")[0], op=op))
    return sorted(out, key=lambda x: x["cycle"])


def bench_cases(cal, max_msgs=30, t_lo=None):
    """TP8 collective RTL bench cases (tools/qwen_coll_tp8_static_links_bench.py --mu-cal): the all-reduce commands of
    every user inside one window of the compiled calendar (<= max_msgs, the issuer's 31 rows less END), the same
    window with the latency user's commands only (its outputs must land on the same cycles: identity), and a
    negative control with one filler command moved onto the previous command's issue window (the engine must fault)."""
    allc = coll_commands(cal)
    t_lo = t_lo if t_lo is not None else cal["single_user_token_cycles"]      # second token of the latency user
    win = [c for c in allc if c["cycle"] >= t_lo][:max_msgs]
    w = cal["inputs"]["ar_words"]
    mu = [[c["cycle"], 0, w] for c in win]
    ref = [[c["cycle"], 0, w] for c in win if c["user"] == 0]
    spans = [(c["cycle"], c["cycle"] + 2 * cal["inputs"]["lu"] + 46 + cal["inputs"]["ls"] + 12 + w) for c in win]
    overl = sum(1 for i in range(len(spans)) for j in range(i + 1, len(spans)) if spans[j][0] < spans[i][1])
    k = next(i for i, c in enumerate(win) if c["user"] != 0 and i > 0)
    bad = [list(x) for x in mu]
    bad[k][0] = mu[k - 1][0] + w // 2                                         # inside the previous command's 256 words
    bad.sort()
    users = sorted({c["user"] for c in win})
    return dict(cases=[
        dict(name="mu_window", kind="pos", cmds=mu, users=[c["user"] for c in win], layers=[c["layer"] for c in win],
             ops=[c["op"] for c in win]),
        dict(name="mu_window_ref_user0", kind="pos", cmds=ref),
        dict(name="mu_window_neg_overlap", kind="neg", cmds=bad, unchecked=True)],
        window=dict(t_lo=t_lo, first=win[0]["cycle"], last=win[-1]["cycle"], messages=len(win), users=users,
                    overlapping_epoch_pairs=overl))


# ---- kv_calendar user dimension ----------------------------------------------------------------------------------------
KV_ROW0 = 64                 # qkd_kv_static_writer :85 / qkd_controller_hbm_calendar ROW0: layer l's KV row = 64 + l
KV_USER_ROW_STRIDE = 256     # qkd_kv_mu_wrow / qkd_kv_mu_rrow (MU-QWEN-HOST): row[9:8] = user, pure bit insertion
KV_EMBED_ROW0 = 24427        # first embedding-table row on the KV die (must stay above every user's KV rows)


def kv_user_rows(users, layers=36):
    """HBM row of user u, layer l on the Qwen KV die = 64 + l + 256*u (coordinator 0jc: the RTL row is the reference).
    This is exactly what the RTL does: qkd_kv_mu_wrow/rrow OR the 2-bit user into row[9:8] of the today row 64 + l, so
    row[7:0] - 64 = layer stays exact for the closed read-return tag.  Checked here: no carry (64 + l < 256), users fit
    the 2-bit field, rows disjoint, below the embedding table."""
    if users > 4 or users < 1:
        raise ScheduleError(f"kv_user_rows: {users} users, the RTL user field is 2 bits")
    if KV_ROW0 + layers > KV_USER_ROW_STRIDE:
        raise ScheduleError(f"kv_user_rows: 64 + {layers} layers carries into the user bits")
    rows = {(u, l): (KV_ROW0 + l) | (u << 8) for u in range(users) for l in range(layers)}
    assert all(r == KV_ROW0 + l + KV_USER_ROW_STRIDE * u for (u, l), r in rows.items())
    assert len(set(rows.values())) == len(rows) and max(rows.values()) < KV_EMBED_ROW0
    return rows


def kv_user_bases(users, layers=36, sectors_per_row=1024):
    """per-PC HBM sector base {row19, sector10} of user u, layer l = kv_user_rows << 10 (static_kv_calendar.sector is
    10 bits: K 0..255, V 512..767); disjoint by construction, checked.  (Was (u*36 + l) << 10 before 0jc: that row map
    did not match the RTL, which keeps row[7:0] = 64 + l and puts the user in row[9:8].)"""
    rows = kv_user_rows(users, layers)
    bases = {k: r * sectors_per_row for k, r in rows.items()}
    spans = sorted((b, b + sectors_per_row) for b in bases.values())
    assert all(x[1] <= y[0] for x, y in zip(spans, spans[1:]))
    return bases


def kv_user_dimension(cal, T=8192, kvp=None):
    """kv_calendar with a user dimension: every user-layer's KV-die HBM PC streams live inside its own attention-service
    window (kvs); the windows are disjoint across users (checked by compile_calendar), so the per-PC command streams of
    two users never share an HBM edge; the per-PC busy edges of one layer (kv_calendar.screen_36_capacity) must fit the
    service window, and every user's rows sit at a disjoint base."""
    from . import kv_calendar as K
    q = dict(K.SOURCED, ring_cdc_core_edges=3, layer_period_core=cal["inputs"]["kv_service"], write_ready_core=0,
             front_nblk=10, ring_depth=64, refresh=K.refresh_from_table(), **(kvp or {}))
    scr = K.screen_36_capacity(T, q)
    svc_hbm = math.floor(cal["inputs"]["kv_service"] * K.SOURCED["core_ps"] / K.SOURCED["hbm_ps"])
    NU = cal["inputs"]["users"]
    bases = kv_user_bases(NU)
    win = []
    for u, seq in cal["schedule"].items():
        for name, t0, b in seq:
            for a, bb in b["windows"].get("kvs", []):
                win.append((t0 + a, t0 + bb, u, name))
    win.sort()
    overlap = [(x, y) for x, y in zip(win, win[1:]) if y[0] < x[1]]
    return dict(context=T, users=NU, pc_busy_hbm_per_layer=scr["pc_busy_hbm_per_layer"], service_window_hbm=svc_hbm,
                pc_streams_fit_service_window=scr["pc_busy_hbm_per_layer"] <= svc_hbm,
                capacity_feasible_in_window=scr["capacity_feasible"], kvs_window_overlaps=len(overlap),
                user_layer_bases=len(bases), row_formula="64 + layer + 256*user (= RTL qkd_kv_mu_wrow/rrow)",
                user_row_stride=KV_USER_ROW_STRIDE,
                base_example={f"u{u}_L{l}": bases[(u, l)] for u in range(NU) for l in (0, 35)},
                note="bases = the RTL row map (qkd_kv_mu_rowoff inserts the stage user into row[9:8]; no job-word field); the HBM PC "
                     "stream of a user-layer starts at its kvs window start, so prefetch never spans another user's window")


# ---- DV compute-die command calendar user relocation (MU-ADOPT-CTLM 10-19) ---------------------------------------------
# qfd_tt_ctlm_dv / qfd_tt_ctlm_dv_lpf NU 4: u_cal = qfd_dv_cmd_cal_mu #(UVM_STRIDE, PIDX_STRIDE, UTAG_LSB, UFOLD 1).  ONE shared
# image is written with user-0 absolute fields and all user fields 0; the playhead of user u adds / inserts:
DV_UVM_STRIDE = 4096      # VM words: the slice VM is 16,384 32-bit words (qfd_dv_vm addr[23:14] == 0) -> 4 users x 4,096
DV_PIDX_STRIDE = 128      # SU program index: the slice PROG store is 512 instructions (9-bit pidx) -> 4 users x 128
DV_UTAG_LSB = 6           # XC (kind 0 sub 0) collective tag bit of the 2-bit user (cmd[23 + 6 +: 2])
DV_VM_WORDS, DV_PIDX_WORDS = 16384, 512


def dv_user_fields(users=4):
    """the per-user command fields the DV calendar writes (qfd_dv_cmd_cal_mu at NU = users, UFOLD 1), for the lowering:
    every relocated region of user 0 must fit [0, stride) so users never overlap and no field carries (carry = fault)."""
    if users < 1 or users > 4:
        raise ScheduleError(f"dv_user_fields: {users} users, the cmd user fields are 2 bits")
    if users * DV_UVM_STRIDE > DV_VM_WORDS or users * DV_PIDX_STRIDE > DV_PIDX_WORDS:
        raise ScheduleError("dv_user_fields: strides x users exceed the slice VM / PROG store")
    return dict(
        users=users, uvm_stride=DV_UVM_STRIDE, pidx_stride=DV_PIDX_STRIDE, utag_lsb=DV_UTAG_LSB,
        user0_vm_window=[0, DV_UVM_STRIDE], user0_pidx_window=[0, DV_PIDX_STRIDE],
        relocated={"PORTS kind 4": "ar_base [27:4], dd_base [51:28], em_base [77:54] += u*UVM_STRIDE",
                   "STN kind 2 dst VM (cmd[24])": "dbase [49:26] += u*UVM_STRIDE",
                   "SU kind 1": "pidx [12:4] += u*PIDX_STRIDE",
                   "XC kind 0 sub 0": "tag bits [23+UTAG_LSB +: 2] = u (image 0)",
                   "STN kind 2 (UFOLD)": "cmd[52:51] = u (image 0; R4 qfd_dv_amax_mu stn_user)",
                   "AMAX kind 6 (UFOLD)": "cmd[9:8] = u (image 0; R4 qfd_dv_amax_mu am_user)"},
        rules=["user-0 VM footprint of every relocated write / landing region < UVM_STRIDE words",
               "user-0 SU programme (pidx) < PIDX_STRIDE; per-user copies at pidx + u*PIDX_STRIDE (loaded per user)",
               "XC tags < 2**UTAG_LSB (user bits 0 in the image); STN cmd[52:51] = AMAX cmd[9:8] = 0 in the image",
               "a filler's first entry T_0 >= 4 + (NU - 1); no two users' entries / segment ends on one edge",
               "fillers' ME work = LOCAL SEG entries of their own segments (the dh start runs the ME programme for user 0 "
               "only) at a non-zero base, without SU o-sync waits (the head's SU accepted count is user 0's)"])


def summary(cal):
    s = {k: v for k, v in cal.items() if k != "schedule"}
    s["schedule_blocks"] = {u: len(v) for u, v in cal["schedule"].items()}
    return s


def frame_feasible_shifts(p=None):
    """pure-shift feasibility on the layer frame: the shifts d (mod P) for which the reference layer block and the
    same block shifted by d share no resource cycle; per resource the forbidden count (the study's lemma assumes one
    window per resource a layer; the tile field has 4, the SU 5, the collective 2 messages)"""
    p = _need(dict(SOURCED, **(p or {})))
    P = p["layer_period"]
    blk = layer_block(p)
    allbad = [False] * P
    per = {}
    for res, iv in blk["windows"].items():
        bad = [False] * P
        for a1, b1 in iv:
            for a2, b2 in iv:
                for d in range(a1 - b2 + 1, b1 - a2):
                    bad[d % P] = True
        per[res] = dict(windows=len(iv), busy=sum(b - a for a, b in iv), forbidden_shifts=sum(bad))
        allbad = [x or y for x, y in zip(allbad, bad)]
    ok = [d for d in range(1, P) if not allbad[d]]
    ok_set = set(ok)
    triple = None
    for d1 in ok:
        for d2 in ok:
            if d2 <= d1 or (d2 - d1) % P not in ok_set:
                continue
            for d3 in ok:
                if d3 > d2 and (d3 - d1) % P in ok_set and (d3 - d2) % P in ok_set:
                    triple = (d1, d2, d3)
                    break
            if triple:
                break
        if triple:
            break
    runs, s0 = [], None
    for d in range(1, P + 1):
        if d < P and d in ok_set:
            s0 = d if s0 is None else s0
        elif s0 is not None:
            runs.append((s0, d))
            s0 = None
    return dict(period=P, per_resource=per, feasible_pair_shifts=len(ok), feasible_runs=runs,
                four_user_pure_shift=triple)


def receipt():
    """every number of the MU-QWEN 10-18 calendar study (results/rtl/mu_qwen_1018/calendar/summary.json)"""
    out = dict(schema="opentallas.qwen.mu_calendar.receipt.v1", grade="modelled (windows measured-old-RTL + priced)",
               layer_source=SRC_LAYER, inputs=dict(SOURCED), frame={}, runs=[], sensitivity=[])
    for occ in ("measured", "priced"):
        out["frame"][occ] = frame_feasible_shifts(dict(occupancy=occ))
    for occ in ("measured", "priced"):
        for gran in ("layer", "op"):
            for hc in (1, 8):
                for pol in ("joint", "priority"):
                    for nu in (1, 2, 3, 4):
                        cal = compile_calendar(dict(users=nu, occupancy=occ, head_chunks=hc), tokens=6,
                                               granularity=gran, policy=pol)
                        out["runs"].append(dict(occupancy=occ, granularity=gran, head_chunks=hc, policy=pol, users=nu,
                                                aggregate_tok_s=round(cal["aggregate_tok_s"], 1),
                                                per_user_tok_s=[round(u["tok_s"], 1) if u["tok_s"] else 0.0
                                                                for u in cal["users"]],
                                                latency_user_identical=cal["latency_user_identical"]))
    base = layer_block
    for drop in ([], ["me"], ["su"], ["kvs"], ["coll"], ["coll.ucie"], ["me", "su"], ["me", "su", "coll"]):
        def lb(p, l0=False, drop=drop):
            b = dict(base(p, l0))
            b["windows"] = {r: v for r, v in b["windows"].items() if not any(r.startswith(d) for d in drop)}
            return b
        globals()["layer_block"] = lb
        try:
            cal = compile_calendar(dict(users=4, occupancy="measured", head_chunks=8), tokens=6, policy="priority")
        finally:
            globals()["layer_block"] = base
        out["sensitivity"].append(dict(resources_ignored=drop, aggregate_tok_s=round(cal["aggregate_tok_s"], 1),
                                       per_user_tok_s=[round(u["tok_s"] or 0, 1) for u in cal["users"]]))
    cal = compile_calendar(dict(users=4, occupancy="measured", head_chunks=8), tokens=6, policy="priority")
    out["of_record"] = dict(call="compile_calendar(dict(users=4, occupancy='measured', head_chunks=8), tokens=6, "
                                 "policy='priority')", summary={k: v for k, v in summary(cal).items() if k != "inputs"},
                            kv_user_dimension=kv_user_dimension(cal))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    r = receipt()
    txt = json.dumps(r, indent=1, default=str)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(txt + "\n")
    best = {}
    for x in r["runs"]:
        k = (x["occupancy"], x["granularity"], x["head_chunks"], x["users"])
        best[k] = max(best.get(k, 0), x["aggregate_tok_s"])
    for k, v in sorted(best.items()):
        print(k, v)
