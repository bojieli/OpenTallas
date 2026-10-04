#!/usr/bin/env python3
"""DSpark (DeepSeek-V4.1's built-in MTP) on the V4.1 HBM comparator: golden trace, RTL bench script and SM operands.

    HDC_V41_ARITH=chunk8 python3 tools/dshbm_dspark_trace.py --out DIR [--drafter dspark|forced] [--ngen 16]
        [--gamma 5] [--sm-steps 1] [--wr 136] [--sr-extra 8]

WHAT IT RUNS.  The golden's own greedy speculative decode (tools/hdc_golden_v41.py Model.generate_spec order) on the
reduced V4.1 vehicle (compiler/models/deepseek-v4.1-flash-reduced-v2, released DSpark structure, seeded weights):
prefill one position a pass (each seeds the three DSpark window caches), then per step: DSpark draft (3 stages over a
block of 5 slots [y, noise x4], the shared LM head, 5 serial Markov-biased argmaxes), one layer-major verify pass of
y, d_1 .. d_gamma, greedy accept, commit (truncate).  Drafter `forced` replaces DSpark with the golden continuation,
one draft corrupted per step at a slot cycling 0 .. gamma (gamma: none), so every accept length 0 .. gamma occurs.
It checks, before writing anything, that the emitted tokens and their logits equal Model.generate's bit for bit and
that the committed state equals the autoregressive run's (Model.generate with DSpark seeding, same positions).

WHAT IT WRITES (DIR):
  script.hex   the bench script of rtl/test/tb_dshbm_dspark.sv: one 128-bit record a line
               {op[8], kind[8], idx[16], pos[32], data[64]} -- per control command the engine-side events the golden
               performs, in the golden's order: window / DSpark-window / compressor-slot / compressed-row / token-ring
               writes (data = a 64-bit content tag of the row: sha256 of its FP32 bits) and gathers (data = the FNV-1a
               fold of the tags the golden's own read returns, in the golden's order), router values (FP32) with the
               expected top-k ids, the expected expert union with per-position masks, and logit rows (FP32 logits,
               FP32 Markov bias) with the golden argmax;
  prompt.hex, force.hex, expect.hex, cfg.json   prompt, forced drafts, expected emitted tokens / per-step accepts;
  final section of script.hex   gathers at the final committed position checked against the AUTOREGRESSIVE run's
               state (window rows of every layer, DSpark rows, compressed rows and index keys, open compressor
               groups, token history): exact rollback, not just equal tokens;
  sm_ops.pkl   (--sm-steps) every SM matvec of the first N speculative steps (draft and verify): weight, the columns
               (positions / block slots sharing one weight pass), golden outputs -- the operands of
               tools/dshbm_dspark_sm_campaign.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "build/models/deepseek-v4.1-flash-reduced-v2").exists():
    os.environ.setdefault("OPENTALLAS_BUILD", "/home/ubuntu/OpenTallas/build")
os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402

F = np.float32
# script opcodes (rtl/test/tb_dshbm_dspark.sv)
OP_CMD, OP_TOK, OP_WR, OP_RD, OP_SEL, OP_RV, OP_VAL, OP_ID, OP_UNION, OP_UID, OP_LG, OP_LV, OP_END = (
    0x01, 0x02, 0x10, 0x11, 0x12, 0x20, 0x21, 0x22, 0x30, 0x31, 0x40, 0x41, 0xFE)
OP_FINAL, OP_EOF = 0xF0, 0xFF
# command ops (rtl/gpu/dshbm/ot_dshbm_pkg.svh)
C_VLAYER, C_VHEAD, C_SEED, C_DSTAGE, C_DHEAD, C_MARKOV = 0, 1, 2, 3, 4, 5
# spec-state kinds
K_WIN_WR, K_WIN_RD, K_DSK_WR, K_DSK_RD, K_SLOT_WR, K_SLOT_RD, K_CK_WR, K_IK_RD, K_CK_SEL, K_TOK_RD = range(1, 11)
FNV0, FNVP, M64 = 0xCBF29CE484222325, 0x100000001B3, (1 << 64) - 1


def tag(*arrs) -> int:
    h = hashlib.sha256()
    for a in arrs:
        h.update(G.bits(np.asarray(a, dtype=F)).tobytes())
    t = int.from_bytes(h.digest()[:8], "little")
    return t or 1


def fold(tags) -> int:
    h = FNV0
    for t in tags:
        h = ((h ^ t) * FNVP) & M64
    return h


def fbits(v) -> int:
    return int(G.bits(np.asarray([v], dtype=F))[0])


class Script:
    def __init__(self):
        self.rec = []

    def put(self, op, kind=0, idx=0, pos=0, data=0):
        assert 0 <= data <= M64 and 0 <= pos < 1 << 32 and 0 <= idx < 1 << 16
        self.rec.append((op, kind, idx, pos, data))

    def hex(self):
        return "".join(f"{op:02x}{k:02x}{i:04x}{p:08x}{d:016x}\n" for op, k, i, p, d in self.rec)


class Tracer(V.Model):
    """The golden model with its engine-side events recorded (no arithmetic changed: every override calls the
    golden's own method and only reads its state)."""

    def __init__(self, config=None):
        super().__init__(config=config or V.CONFIG)
        self.buf = None          # list the current command's events go to (None: not recording)
        self.mvlog = None        # SM matvec capture (list) or None
        self.cur = None          # (phase, index) of the current command, for the matvec capture
        self.anon = {}           # captured weights that are not checkpoint tensors (views, fused), by content name
        self.wname = {id(v): k for k, v in self.w.items()}
        self.wname.update({id(v.q): k for k, v in self.w.items() if isinstance(v, V.Q8)})

    # -- events -------------------------------------------------------------------------------------
    def ev(self, *r):
        if self.buf is not None:
            self.buf.append(r)

    def layer(self, L, ctx, state, trace=None):
        if self.buf is not None and L in self.engram.layer_ids:
            hist = ctx["hist"]
            toks = [int(hist[-1 - s]) + 1 if s < len(hist) else 0 for s in range(self.engram.n)]
            self.ev(OP_RD, K_TOK_RD, 0, ctx["pos"], fold(toks))
        self.cur = ("V", L)
        return super().layer(L, ctx, state, trace)

    def attention(self, L, x, pos, state, trace, ctx):
        yarn = self.ratio[L] > 0
        src = self.kv_of.get(L)
        nck = len(state["ckv"][src]) if yarn else 0
        y = super().attention(L, x, pos, state, trace, ctx)
        W = self.window
        self.ev(OP_WR, K_WIN_WR, L, pos, tag(state["win"][L][-1]))
        self.ev(OP_RD, K_WIN_RD, L, pos, fold(tag(r) for r in state["win"][L][-W:]))
        if yarn:
            si = self.kv_src.index(src)
            r = self.ratio[src]
            if L == src:
                if r > 1:
                    self.ev(OP_WR, K_SLOT_WR, si, pos, tag(*state["slotrec"][L][pos]))
                    if (pos + 1) % r == 0:
                        self.ev(OP_RD, K_SLOT_RD, si, pos,
                                fold(tag(*state["slotrec"][L][p]) for p in range(pos - r + 1, pos + 1)))
                if len(state["ckv"][src]) != nck:
                    assert len(state["ckv"][src]) == nck + 1 and (pos + 1) % r == 0
                    self.ev(OP_WR, K_CK_WR, si, pos, tag(state["ckv"][src][-1], state["ik"][src][-1]))
            if L == self.idx_of[L]:
                n = (pos + 1) // r
                if n:
                    self.ev(OP_RD, K_IK_RD, si, pos,
                            fold(tag(state["ckv"][src][i], state["ik"][src][i]) for i in range(n)))
            sel = ctx["sel"]
            self.ev(OP_SEL, K_CK_SEL, si, len(sel),
                    fold(tag(state["ckv"][src][i], state["ik"][src][i]) for i in sel), list(sel))
        return y

    def moe(self, L, x, trace):
        t = {}
        y = super().moe(L, x, t)
        vals = np.asarray(t[f"L{L}.router"], dtype=F)
        self.ev(OP_RV, 1 if L >= self.L else 0, 0, 0, 0, [fbits(v) for v in vals], [int(i) for i in t[f"L{L}.experts"]])
        if trace is not None:
            trace.update(t)
        return y

    def dspark_window(self, st, anchor, state):
        rows = super().dspark_window(st, anchor, state)
        self.ev(OP_RD, K_DSK_RD, st, anchor, fold(tag(r) for r in rows))
        return rows

    def dspark_seed(self, mh, pos, state, trace=None):
        self.cur = ("SEED", 0)
        super().dspark_seed(mh, pos, state, trace)
        for st in range(self.n_mtp):
            self.ev(OP_WR, K_DSK_WR, st, pos, tag(state["dsk"][st][-1]))

    def dspark_stage(self, L, hs, pres, anchor, state):
        self.cur = ("D", L - self.L)
        return super().dspark_stage(L, hs, pres, anchor, state)

    # -- the draft, with the pre-Markov logits and the Markov bias exposed (the golden's draft, line for line) ---
    def draft_traced(self, y, anchor, state, stage_bufs):
        B = self.dspark_block
        ids = [int(y)] + [self.noise_id] * (B - 1)
        hs = [np.repeat(self.w["embed.weight"][t][None, :], self.hc, axis=0).astype(F) for t in ids]
        pres = [np.array([1, 0, 0, 0], dtype=F)[:self.hc] for _ in ids]
        for st in range(self.n_mtp):
            self.buf = stage_bufs[st]
            hs, pres = self.dspark_stage(self.L + st, hs, pres, anchor, state)
        self.buf = None
        Lf = self.L + self.n_mtp - 1
        self.cur = ("DH", 0)
        xh = [V.to_bf16(self.hc_pre(h, p)) for h, p in zip(hs, pres)]
        logits = [V.mv(self.w["head.weight"], V.rmsnorm_bf16(x, self.lw(Lf, "norm.weight"), self.eps)) for x in xh]
        out, rows = [int(y)], []
        emb, mhead = self.lw(Lf, "markov_head.embed.weight"), self.lw(Lf, "markov_head.head.weight")
        for i in range(B):
            self.cur = ("MK", i)
            e = emb[out[i]]
            bias = V.mv(mhead, e)
            pre = logits[i]
            logits[i] = V.add(pre, bias)
            rows.append((pre, bias, out[i]))
            out.append(int(np.argmax(logits[i])))
        return out[1:], logits, rows


# -- SM matvec capture --------------------------------------------------------------------------------------
_ORIG = dict(linear_q=V.linear_q, mv=V.mv, matvec_c=V.matvec_c)
_DEPTH = [0]
_TR: list = [None]


def _wrap(name):
    f = _ORIG[name]

    def g(*a, **k):
        tr = _TR[0]
        rec = tr is not None and tr.mvlog is not None and _DEPTH[0] == 0
        _DEPTH[0] += 1
        try:
            y = f(*a, **k)
        finally:
            _DEPTH[0] -= 1
        if rec and not (name == "matvec_c" and k.get("cls", "me") == "he"):
            w = a[0]
            key = w.q if isinstance(w, V.Q8) else w
            nm = tr.wname.get(id(key))
            if nm is None:      # a view (grouped wo_a) or a fused weight (compressor wkv|wgate)
                nm = "anon:" + hashlib.sha1(G.bits(np.asarray(w.dense() if isinstance(w, V.Q8) else w,
                                                              dtype=F)).tobytes()).hexdigest()[:16]
                tr.anon.setdefault(nm, w)
            tr.mvlog.append(dict(fn=name, ctx=tr.cur, name=nm, x=np.array(a[1], dtype=F), y=np.array(y, dtype=F)))
        return y
    return g


for _n in _ORIG:
    setattr(V, _n, _wrap(_n))


# -- the run ------------------------------------------------------------------------------------------------
def emit_cmd(S, op, idx, ncol, pos, toks, tok=0):
    S.put(OP_CMD, op, idx, pos, (tok << 32) | ncol)
    for t in toks:
        S.put(OP_TOK, 0, 0, 0, int(t))


def emit_events(S, evs, union_cols, n_exp):
    """evs: the recorded events of one command; union_cols: emit the union of the router selections (columns =
    router vectors in order)."""
    col = 0
    sel_all = []
    for e in evs:
        op = e[0]
        if op in (OP_WR, OP_RD):
            S.put(op, e[1], e[2], e[3], e[4])
        elif op == OP_SEL:
            S.put(OP_SEL, e[1], e[2], e[3], e[4])
            for i in e[5]:
                S.put(OP_VAL, 0, 0, 0, int(i))
        elif op == OP_RV:
            vals, ids = e[5], e[6]
            S.put(OP_RV, e[1], col, len(vals), len(ids))
            for v in vals:
                S.put(OP_VAL, 0, 0, 0, v)
            for i in ids:
                S.put(OP_ID, 0, 0, 0, i)
            sel_all.append(ids)
            col += 1
    if union_cols and sel_all:
        u = sorted(set(i for ids in sel_all for i in ids))
        S.put(OP_UNION, 1 if evs and any(e[0] == OP_RV and e[1] == 1 for e in evs) else 0, 0, len(u), len(sel_all))
        for i in u:
            mask = sum(1 << j for j, ids in enumerate(sel_all) if i in ids)
            S.put(OP_UID, 0, 0, 0, (mask << 16) | i)
    return sel_all


def emit_logits(S, col, lg, gold_tok, bias=None):
    S.put(OP_LG, 1 if bias is not None else 0, col, len(lg), gold_tok)
    lb = G.bits(np.asarray(lg, dtype=F))
    bb = G.bits(np.asarray(bias, dtype=F)) if bias is not None else np.zeros(len(lg), np.uint32)
    for a, b in zip(lb, bb):
        S.put(OP_LV, 0, 0, 0, (int(b) << 32) | int(a))


def run(a):
    cfgp = V.CONFIG
    if a.window:
        # a window-size variant of the reduced vehicle (same weights): the shipped reduced window (128) equals its
        # max_seq_len, so no ring ever wraps; a short window makes rejected rows land in live ring slots
        c = json.loads(V.CONFIG.read_text())
        c["window_size"] = a.window
        cfgp = a.out / "inference_config_window.json"
        cfgp.write_text(json.dumps(c, indent=1) + "\n")
    m = Tracer(cfgp)
    _TR[0] = m
    prompt, _ = V.prompt_and_expected()
    prompt = list(prompt)
    gamma, ngen, B = a.gamma, a.ngen, m.dspark_block
    # golden autoregressive reference (long enough for the forced drafter and the final-state check)
    ar_len = ngen + 2 * B + 4
    ref = V.Model(config=cfgp)
    ar_tok, ar_lg = ref.generate(prompt, ar_len, mtp_state=True)
    plen = len(prompt)

    S = Script()
    state = m.new_state(mtp=True)
    # ---- prefill: one position a pass ----
    logits = None
    for p, t in enumerate(prompt):
        bufs = {}
        m.buf = None
        orig_layer = m.layer

        def layer_hook(L, ctx, st_, trace=None, _b=bufs):
            m.buf = _b.setdefault(L, [])
            return orig_layer(L, ctx, st_, trace)
        m.layer = layer_hook
        seed_buf = []
        orig_seed = m.dspark_seed

        def seed_hook(mh, pos, st_, trace=None):
            m.buf = seed_buf
            return orig_seed(mh, pos, st_, trace)
        m.dspark_seed = seed_hook
        logits = m.forward_positions([t], p, state)[0]
        m.layer, m.dspark_seed, m.buf = orig_layer, orig_seed, None
        for L in range(m.L):
            emit_cmd(S, C_VLAYER, L, 1, p, [t])
            emit_events(S, bufs.get(L, []), True, m.n_exp)
            S.put(OP_END)
        emit_cmd(S, C_VHEAD, 0, 1, p, [t])
        emit_logits(S, 0, logits, int(np.argmax(logits)))
        S.put(OP_END)
        emit_cmd(S, C_SEED, 0, 1, p, [t])
        emit_events(S, seed_buf, False, 0)
        S.put(OP_END)
    q, y = plen - 1, int(np.argmax(logits))
    out, rows, steps = [y], [logits], []
    max_pos = int(m.c["max_seq_len"])
    force_rows = []
    sm_ops = []
    step = 0
    while len(out) < ngen:
        g = min(gamma, max_pos - 2 - q)
        cap = step < a.sm_steps
        m.mvlog = [] if cap else None
        drafts = []
        if g > 0:
            if a.drafter == "dspark":
                stage_bufs = [[] for _ in range(m.n_mtp)]
                d_all, d_lg, mk = m.draft_traced(y, q, state, stage_bufs)
                if step < 2:     # the traced draft is the golden's draft, bit for bit
                    mvl, m.mvlog = m.mvlog, None
                    g_all, g_lg = V.Model.draft(m, y, q, state)
                    m.mvlog = mvl
                    assert g_all == d_all and all(np.array_equal(G.bits(u), G.bits(v)) for u, v in zip(g_lg, d_lg))
                drafts = d_all[:g]
                for st in range(m.n_mtp):
                    emit_cmd(S, C_DSTAGE, st, B, q, [y])
                    emit_events(S, stage_bufs[st], True, m.dspark_n_exp)
                    S.put(OP_END)
                emit_cmd(S, C_DHEAD, 0, B, q, [y])
                S.put(OP_END)
                for i, (pre, bias, tin) in enumerate(mk[:g]):      # the loop runs g Markov steps (golden: B; d_g+1.. unused)
                    emit_cmd(S, C_MARKOV, i, 1, q, [], tok=tin)
                    emit_logits(S, i, pre, d_all[i], bias)
                    S.put(OP_END)
            else:
                cont = ar_tok      # token at position plen + i
                drafts = [int(cont[q + 1 + i - plen]) for i in range(1, g + 1)]
                c = step % (g + 1)
                if c < g:
                    drafts[c] = (drafts[c] + 1) % int(m.c["vocab_size"])
                force_rows.append(drafts + [0] * (B - len(drafts)))
        # ---- verify: layer-major over y, d_1 .. d_g ----
        toks = [y] + drafts
        bufs = {}
        orig_layer = m.layer

        def layer_hook(L, ctx, st_, trace=None, _b=bufs):
            m.buf = _b.setdefault(L, [])
            return orig_layer(L, ctx, st_, trace)
        m.layer = layer_hook
        seed_buf = []
        orig_seed = m.dspark_seed

        def seed_hook(mh, pos, st_, trace=None):
            m.buf = seed_buf
            return orig_seed(mh, pos, st_, trace)
        m.dspark_seed = seed_hook
        lgs = m.forward_positions(toks, q + 1, state)
        m.layer, m.dspark_seed, m.buf = orig_layer, orig_seed, None
        tg = [int(np.argmax(lg)) for lg in lgs]
        acc = 0
        while acc < len(drafts) and drafts[acc] == tg[acc]:
            acc += 1
        m.truncate(state, q + 2 + acc)
        n_exp_union = []
        for L in range(m.L):
            emit_cmd(S, C_VLAYER, L, len(toks), q + 1, toks)
            sel = emit_events(S, bufs.get(L, []), True, m.n_exp)
            n_exp_union.append(len(set(i for s in sel for i in s)))
            S.put(OP_END)
        emit_cmd(S, C_VHEAD, 0, len(toks), q + 1, toks)
        for j, lg in enumerate(lgs):
            emit_logits(S, j, lg, tg[j])
        S.put(OP_END)
        emit_cmd(S, C_SEED, 0, len(toks), q + 1, toks)
        emit_events(S, seed_buf, False, 0)
        S.put(OP_END)
        steps.append(dict(anchor=q, drafts=drafts, targets=tg, accepted=acc, union_per_layer=n_exp_union))
        if cap:
            sm_ops.append(dict(step=step, anchor=q, ops=m.mvlog))
        m.mvlog = None
        out += tg[:acc + 1]
        rows += lgs[:acc + 1]
        q, y = q + 1 + acc, tg[acc]
        step += 1
    out, rows = out[:ngen], rows[:ngen]
    # ---- golden checks ----
    assert out == ar_tok[:ngen], (out, ar_tok[:ngen])
    assert all(np.array_equal(G.bits(u), G.bits(v)) for u, v in zip(rows, ar_lg[:ngen]))
    n_final = q + 1
    ref2 = V.Model(config=cfgp)
    ref2.generate(prompt, n_final - plen + 1, mtp_state=True)
    ars = ref2.last_state
    assert len(ars["tokens"]) == n_final == len(state["tokens"]), (len(ars["tokens"]), n_final, len(state["tokens"]))
    assert V.state_digest(ars) == V.state_digest(state), "committed state differs from the autoregressive state"
    # ---- final: gathers at the last committed position against the AUTOREGRESSIVE state ----
    S.put(OP_FINAL, 0, 0, n_final, 0)
    W = m.window
    p = n_final - 1
    toks = [int(ars["tokens"][p - s]) + 1 if p - s >= 0 else 0 for s in range(m.engram.n)]
    S.put(OP_RD, K_TOK_RD, 0, p, fold(toks))
    for L in range(m.L):
        S.put(OP_RD, K_WIN_RD, L, p, fold(tag(r) for r in ars["win"][L][-W:]))
    for st in range(m.n_mtp):
        S.put(OP_RD, K_DSK_RD, st, p, fold(tag(r) for r in V.Model.dspark_window(ref2, st, p, ars)))
    for si, s in enumerate(m.kv_src):
        r = m.ratio[s]
        n = n_final // r
        if n:
            S.put(OP_RD, K_IK_RD, si, p, fold(tag(ars["ckv"][s][i], ars["ik"][s][i]) for i in range(n)))
        if r > 1 and n_final % r:
            S.put(OP_RD, K_SLOT_RD, si, p,
                  fold(tag(*ars["slotrec"][s][pp]) for pp in range(n_final - n_final % r, n_final)))
    S.put(OP_EOF)
    return m, prompt, out, steps, S, force_rows, sm_ops, n_final


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--drafter", choices=("dspark", "forced"), default="dspark")
    ap.add_argument("--ngen", type=int, default=16)
    ap.add_argument("--gamma", type=int, default=5)
    ap.add_argument("--sm-steps", type=int, default=0)
    ap.add_argument("--window", type=int, default=0, help="window-size variant (ring-wrap rollback check)")
    a = ap.parse_args()
    assert V.ARITH == "chunk8", "the HBM comparator's SM runs the R-ARITH chunk-8 contract"
    a.out.mkdir(parents=True, exist_ok=True)
    m, prompt, out, steps, S, force_rows, sm_ops, n_final = run(a)
    (a.out / "script.hex").write_text(S.hex())
    (a.out / "prompt.hex").write_text("".join(f"{t:08x}\n" for t in prompt))
    (a.out / "force.hex").write_text("".join(f"{t:08x}\n" for r in force_rows for t in r) or "00000000\n")
    exp = list(out) + [s["accepted"] for s in steps]
    (a.out / "expect.hex").write_text("".join(f"{t:08x}\n" for t in exp))
    cfg = dict(drafter=a.drafter, gamma=a.gamma, window_override=a.window or None, ngen=a.ngen, prompt=prompt, plen=len(prompt), tokens=out,
               steps=steps, n_final=n_final, records=len(S.rec), arith=V.ARITH,
               model=dict(layers=m.L, dim=m.dim, vocab=int(m.c["vocab_size"]), n_exp=m.n_exp, k_exp=m.k_exp,
                          d_exp=m.dspark_n_exp, d_k=m.dspark_k_exp, block=m.dspark_block, window=m.window,
                          n_mtp=m.n_mtp, kv_src=m.kv_src, ratios=[m.ratio[s] for s in m.kv_src],
                          engram_n=m.engram.n, max_seq_len=int(m.c["max_seq_len"])),
               golden=dict(tokens_equal_autoregressive=True, logits_bit_equal=True,
                           committed_state_digest_equal_autoregressive=True))
    (a.out / "cfg.json").write_text(json.dumps(cfg, indent=1) + "\n")
    if sm_ops:
        with open(a.out / "sm_ops.pkl", "wb") as fh:
            pickle.dump(dict(steps=sm_ops, anon=m.anon), fh)
    print(json.dumps({k: cfg[k] for k in ("drafter", "tokens", "n_final", "records")}))
    print("accepted per step", [s["accepted"] for s in steps])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
