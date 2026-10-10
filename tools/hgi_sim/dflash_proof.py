#!/usr/bin/env python3
"""DFlash on HGI-1, functional proof: the step program (tools/hgi_sim/dflash.py) on the simulator against a numpy
golden built on the same arithmetic library, on a tiny Qwen3 target (random BF16 weights, 6 layers, TP4 shapes scaled
down) and a tiny DFlash drafter (2 layers, target layers [1, 3], random BF16 weights).  The golden's target is the
qwen_r25 golden (QwenR25.layer / head); its drafter follows the bindings in dflash.py.

Checked bit for bit, every step, every die:
  * draft ids D[1..B-1];  * committed tokens (TOKX) and the count k;
  * target KV rows written at [pos, pos + B) for every layer (FP8 bytes);
  * drafter KV rows written at [pos - B, pos) for every drafter layer (BF16 bytes);
  * captured features at [pos, pos + B) (BF16 bytes).
And end to end (lossless greedy speculation): the committed token stream over several steps equals plain AR greedy
decoding (QwenR25, one position at a time) from the same state.  One step runs with ORACLE drafts (D overwritten with
the AR continuation through the machine's hook) so that full acceptance, k = B, and the next step's context rows are
exercised; mutants (a causal-mask tail not zeroed; the drafter attending causally) must fail.

    python3 -m hgi_sim.dflash_proof --out REC.json
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import qwen_r25_golden as R  # noqa: E402
import hdc_golden as G  # noqa: E402

from hgi_sim import dflash as D  # noqa: E402
from hgi_sim import lib as A  # noqa: E402
from hgi_sim import qwen_compiler as QC  # noqa: E402
from hgi_sim import test_tiny as TT  # noqa: E402
from hgi_sim.machine import UNITS, Die, Fault, Machine, fp8_encode  # noqa: E402
from hgi_sim.qwen_proof import md_words  # noqa: E402
from hgi_sim.records import decode_program, encode_program  # noqa: E402

F = np.float32
TP = QC.TP
bf = A.to_bf16


def bf16_bytes(v):
    return QC.bf16_bytes(v)


def rand_bf16(rng, shape, s):
    return bf((rng.standard_normal(shape) * s).astype(F))


class Drafter:
    """Tiny DFlash drafter weights (BF16 values in FP32 arrays), the released layout: per layer q/k/v/o, gate/up/down,
    two norms, q/k norms; fc [H, nf*H]; hidden_norm; norm."""

    def __init__(self, dcfg, seed=5):
        rng = np.random.default_rng(seed)
        H, NH, KV, HD, FF = (dcfg[k] for k in ("hidden_size", "num_attention_heads", "num_key_value_heads", "head_dim",
                                               "intermediate_size"))
        nf = len(dcfg["dflash_config"]["target_layer_ids"])
        self.c = dcfg
        self.layers = []
        for _ in range(dcfg["num_hidden_layers"]):
            self.layers.append(dict(
                q=rand_bf16(rng, (NH * HD, H), 0.06), k=rand_bf16(rng, (KV * HD, H), 0.06),
                v=rand_bf16(rng, (KV * HD, H), 0.06), o=rand_bf16(rng, (H, NH * HD), 0.04),
                gate=rand_bf16(rng, (FF, H), 0.06), up=rand_bf16(rng, (FF, H), 0.06), down=rand_bf16(rng, (H, FF), 0.04),
                ln1=bf(rng.uniform(0.5, 1.5, H).astype(F)), ln2=bf(rng.uniform(0.5, 1.5, H).astype(F)),
                qn=bf(rng.uniform(0.5, 1.5, HD).astype(F)), kn=bf(rng.uniform(0.5, 1.5, HD).astype(F))))
        self.fc = rand_bf16(rng, (H, nf * H), 0.03)
        self.hn = bf(rng.uniform(0.5, 1.5, H).astype(F))
        self.norm = bf(rng.uniform(0.5, 1.5, H).astype(F))


def drafter_image(g: D.DGeom, dr: Drafter, d):
    H, HD, nq, nk, ff = g.H, g.HD, g.nq, g.nk, g.ff
    HT = H // TP
    buf = np.zeros(g.dnorm + D.al(H * 2), dtype=np.uint8)
    for i, Lw in enumerate(dr.layers):
        o0 = i * g.dlayer_bytes

        def w(name, arr):
            b = bf16_bytes(np.ascontiguousarray(arr)).reshape(-1)
            buf[o0 + g.dlay[name]:o0 + g.dlay[name] + b.size] = b
        q = Lw["q"][d * nq * HD:(d + 1) * nq * HD]
        k = Lw["k"][d * nk * HD:(d + 1) * nk * HD]
        v = Lw["v"][d * nk * HD:(d + 1) * nk * HD]
        w("qkv", np.concatenate([q, k, v]))
        w("o", Lw["o"][:, d * nq * HD:(d + 1) * nq * HD])
        w("gu", np.concatenate([Lw["gate"][d * ff:(d + 1) * ff], Lw["up"][d * ff:(d + 1) * ff]]))
        w("down", Lw["down"][:, d * ff:(d + 1) * ff])
        for n_ in ("ln1", "ln2", "qn", "kn"):
            w(n_, Lw[n_])
    for j in range(len(g.caps)):
        b = bf16_bytes(np.ascontiguousarray(dr.fc[d * HT:(d + 1) * HT, j * H:(j + 1) * H])).reshape(-1)
        buf[g.dfc + j * g.dfc_blk:g.dfc + j * g.dfc_blk + b.size] = b
    b = bf16_bytes(dr.hn)
    buf[g.dhn:g.dhn + b.size] = b
    b = bf16_bytes(dr.norm)
    buf[g.dnorm:g.dnorm + b.size] = b
    return buf


# ----------------------------------------------------------------------------------------------------------------
# golden state and step
# ----------------------------------------------------------------------------------------------------------------
class Gold:
    def __init__(self, model: R.QwenR25, dr: Drafter, g: D.DGeom, pos0, seed=11):
        rng = np.random.default_rng(seed)
        self.m, self.dr, self.g = model, dr, g
        KV, HD, ctx, H = model.KV, model.HD, g.ctx, model.H
        self.tK = np.zeros((model.L, KV, ctx, HD), dtype=F)
        self.tV = np.zeros_like(self.tK)
        for i in range(model.L):
            Kc, Vc = R.synthetic_kv(model, i, pos0)
            self.tK[i, :, :pos0], self.tV[i, :, :pos0] = Kc[:, :pos0], Vc[:, :pos0]
        nf = len(g.caps)
        self.ctxf = np.zeros((ctx, nf, H), dtype=F)
        self.ctxf[:pos0] = bf((rng.standard_normal((pos0, nf, H)) * 1.5).astype(F))
        nD = len(dr.layers)
        self.dK = np.zeros((nD, KV, ctx, HD), dtype=F)
        self.dV = np.zeros_like(self.dK)
        self.dK[:, :, :pos0] = bf((rng.standard_normal((nD, KV, pos0, HD))).astype(F))
        self.dV[:, :, :pos0] = bf((rng.standard_normal((nD, KV, pos0, HD)) * 0.5).astype(F))

    def snapshot(self):
        return copy.deepcopy((self.tK, self.tV, self.ctxf, self.dK, self.dV))

    # drafter pieces
    def _proj(self, W, x):
        return A.sm_bf16(W, x)

    def draft(self, pos, anchor, B, causal=False):
        m, dr, g = self.m, self.dr, self.g
        H, HD, NH, KV = m.H, m.HD, m.NH, m.KV
        nq, nk, ff = g.nq, g.nk, g.ff
        eps = F(m.eps)
        grp = NH // KV
        HT = H // TP
        nf = len(g.caps)
        # 1. context rows [pos - B, pos)
        for c in range(B):
            r = pos - B + c
            parts = []
            for d in range(TP):
                tj = [self._proj(dr.fc[d * HT:(d + 1) * HT, j * H:(j + 1) * H], self.ctxf[r, j]) for j in range(nf)]
                parts.append(A.pairwise(tj))
            fco = np.concatenate(parts)
            hc = bf(A.row_norm(fco, dr.hn, eps))
            cos, sin = A.rope_tables(r, HD, m.theta)
            for li, Lw in enumerate(dr.layers):
                k = self._proj(Lw["k"], hc).reshape(KV, HD)
                v = self._proj(Lw["v"], hc).reshape(KV, HD)
                kn = A.row_norm(k.reshape(-1), Lw["kn"], eps, HD).reshape(KV, HD)
                self.dK[li, :, r] = bf(A.rope_adj(kn, cos[0], sin[0]))
                self.dV[li, :, r] = bf(v)
        # 2. block
        x = np.stack([m.embed(anchor)] + [m.embed(g.mask_id)] * (B - 1)).astype(F)
        scale = F(1.0 / np.sqrt(HD))
        for li, Lw in enumerate(dr.layers):
            qs, kb, vb = [], np.zeros((KV, B, HD), F), np.zeros((KV, B, HD), F)
            for s in range(B):
                h = bf(A.row_norm(x[s], Lw["ln1"], eps))
                q = self._proj(Lw["q"], h)
                k = self._proj(Lw["k"], h)
                v = self._proj(Lw["v"], h)
                qn = A.row_norm(q, Lw["qn"], eps, HD).reshape(NH, HD)
                kn = A.row_norm(k, Lw["kn"], eps, HD).reshape(KV, HD)
                cos, sin = A.rope_tables(pos + s, HD, m.theta)
                qs.append(bf(A.rope_adj(qn, cos[0], sin[0])))
                kb[:, s] = bf(A.rope_adj(kn, cos[0], sin[0]))
                vb[:, s] = bf(v.reshape(KV, HD))
            for s in range(B):
                attn = np.empty((NH, HD), F)
                nb = s + 1 if causal else B
                for hh in range(NH):
                    kv = hh // grp
                    K = np.concatenate([self.dK[li, kv, :pos], kb[kv, :nb]])
                    Vr = np.concatenate([self.dV[li, kv, :pos], vb[kv, :nb]])
                    e, Z, _ = A.softmax_e_z(A.att_qk(qs[s][hh], K), scale)
                    attn[hh] = A.div(A.att_pv(bf(e), Vr), Z)
                o = A.pairwise([self._proj(Lw["o"][:, d * nq * HD:(d + 1) * nq * HD],
                                           attn[d * nq:(d + 1) * nq].reshape(-1)) for d in range(TP)])
                x[s] = A.add(x[s], o)
            for s in range(B):
                h2 = bf(A.row_norm(x[s], Lw["ln2"], eps))
                gg = self._proj(Lw["gate"], h2)
                uu = self._proj(Lw["up"], h2)
                act = A.glu(gg, uu, out_bf16=True)
                dn = A.pairwise([self._proj(Lw["down"][:, d * ff:(d + 1) * ff], act[d * ff:(d + 1) * ff])
                                 for d in range(TP)])
                x[s] = A.add(x[s], dn)
        ids = [None]
        for s in range(1, B):
            hf = bf(A.row_norm(x[s], dr.norm, eps))
            logits, _ = m.matvec(hf, "lm_head")
            ids.append(int(np.argmax(logits)))
        return ids

    def verify(self, pos, toks):
        m, g = self.m, self.g
        B = len(toks)
        xs = [m.embed(t) for t in toks]
        for i in range(m.L):
            for s in range(B):
                xs[s] = m.layer(i, xs[s], pos + s, self.tK[i], self.tV[i])
            if i in g.caps:
                j = g.caps.index(i)
                for s in range(B):
                    self.ctxf[pos + s, j] = bf(xs[s])
        post = []
        for s in range(B):
            _, tok = m.head(xs[s])
            post.append(tok)
        return post

    def step(self, pos, anchor, B, oracle=None, causal_draft=False):
        d = self.draft(pos, anchor, B, causal=causal_draft)
        if oracle is not None:
            d = [None] + list(oracle[:B - 1])
        post = self.verify(pos, [anchor] + d[1:])
        k = 1
        while k < B and d[k] == post[k - 1]:
            k += 1
        return d, post, k


def ar_decode(model, gold_init, pos0, tok0, n):
    """Plain AR greedy from the same state (QwenR25, one position at a time)."""
    tK, tV = copy.deepcopy(gold_init[0]), copy.deepcopy(gold_init[1])
    out, tok, pos = [], tok0, pos0
    for _ in range(n):
        x = model.embed(tok)
        for i in range(model.L):
            x = model.layer(i, x, pos, tK[i], tV[i])
        _, tok = model.head(x)
        out.append(tok)
        pos += 1
    return out


# ----------------------------------------------------------------------------------------------------------------
# the machine side
# ----------------------------------------------------------------------------------------------------------------
def build_machine(model, dr, g, gold, cfg):
    t = g.t
    hbms, _ = QC.build_images(model, t, list(range(model.L)),
                              kv_state=lambda i: (gold.tK[i], gold.tV[i]))
    ctx, H, HD = g.ctx, g.H, g.HD
    for d, hb in enumerate(hbms):
        hb.add(g.hbm["DWEIGHTS"], drafter_image(g, dr, d), "DWEIGHTS")
        dk = np.zeros(g.dkv_layer * len(dr.layers), dtype=np.uint8)
        for li in range(len(dr.layers)):
            for h in range(g.nk):
                kvh = d * g.nk + h
                for kind, src in ((0, gold.dK), (1, gold.dV)):
                    o = li * g.dkv_layer + (h * 2 + kind) * g.dkv_plane
                    dk[o:o + ctx * HD * 2] = bf16_bytes(src[li, kvh].reshape(-1)).reshape(-1)
        hb.add(g.hbm["DKVC"], dk, "DKVC")
        hb.add(g.hbm["CTXF"], bf16_bytes(gold.ctxf.reshape(-1)).reshape(-1).copy(), "CTXF")
        hb.add(g.hbm["DBLK"], np.zeros(g.dblk_layer * len(dr.layers), dtype=np.uint8), "DBLK")
        cn = np.zeros(g.cnt_one + 4, dtype=np.uint8)
        cn[:g.cnt_one] = np.arange(g.cnt_n, dtype=np.uint32).view(np.uint8)
        cn[g.cnt_one:] = np.asarray([1.0], dtype=F).view(np.uint8)
        hb.add(g.hbm["CNTT"], cn, "CNTT")
        hb.add(g.hbm["MBOX"], np.zeros(8 * g.B + 64, dtype=np.uint8), "MBOX")
    dies = [Die(d, hbms[d]) for d in range(TP)]
    M = Machine(dies, UNITS)
    err = M.cfg_commit(md_words(cfg))
    assert not err, err
    return M


def run_step(M, recs, image, anchor, pos, g, oracle=None):
    recs_ = decode_program(image)
    for r, r0 in zip(recs_, recs):
        r.tag, r.family = r0.tag, r0.family

    def hook(Mm, r, L):
        if oracle is not None and r.tag == f"draft.merge.s{g.B - 1}":
            for die in Mm.dies:
                a = g.vm["D"][0]
                die.vm[a + 1:a + g.B] = np.asarray(oracle[:g.B - 1], dtype=np.uint32)
    M.tokx = None
    tok, _ = M.run(image, anchor, pos, hash_bufs=False, hook=hook, recs=recs_)
    dd = [[int(x) for x in die.vm[g.vm["D"][0] + 1:g.vm["D"][0] + g.B]] for die in M.dies]
    return M.tokx, dd


def hbm_rows(die, base, off, n):
    buf, o, _ = die.hbm.find(base + off, n)
    return buf[o:o + n]


def compare_state(M, g, gold, pos, model, dr):
    """Target KV rows [pos, pos+B), drafter KV rows [pos-B, pos), CTXF rows [pos, pos+B): bytes, every die."""
    rows = []
    t, B, HD = g.t, g.B, g.HD
    for d, die in enumerate(M.dies):
        okT = okD = True
        for i in range(model.L):
            for h in range(g.nk):
                kvh = d * g.nk + h
                for kind, src in ((0, gold.tK), (1, gold.tV)):
                    off = i * t.kv_layer + (h * 2 + kind) * t.kv_plane + pos * HD
                    got = hbm_rows(die, g.hbm["KV"], off, B * HD)
                    okT &= bool(np.array_equal(got, fp8_encode(src[i, kvh, pos:pos + B].reshape(-1))))
        for li in range(len(dr.layers)):
            for h in range(g.nk):
                kvh = d * g.nk + h
                for kind, src in ((0, gold.dK), (1, gold.dV)):
                    off = li * g.dkv_layer + (h * 2 + kind) * g.dkv_plane + (pos - B) * HD * 2
                    got = hbm_rows(die, g.hbm["DKVC"], off, B * HD * 2)
                    okD &= bool(np.array_equal(got, bf16_bytes(src[li, kvh, pos - B:pos].reshape(-1))))
        got = hbm_rows(die, g.hbm["CTXF"], pos * g.ctxf_row, B * g.ctxf_row)
        okC = bool(np.array_equal(got, bf16_bytes(gold.ctxf[pos:pos + B].reshape(-1))))
        rows.append(dict(die=d, target_kv_rows=okT, drafter_kv_rows=okD, captured_features=okC))
    return rows


def campaign(B, steps, oracle_step, mutant=None, log=print):
    tmp = Path(tempfile.mkdtemp(prefix="hgi_dflash_"))
    TT.CFG = dict(TT.CFG, num_hidden_layers=6)
    TT.write_snapshot(tmp)
    model = R.QwenR25(tmp, tmp / "img")
    cfg = model.ck.cfg
    dcfg = dict(hidden_size=cfg["hidden_size"], num_attention_heads=cfg["num_attention_heads"],
                num_key_value_heads=cfg["num_key_value_heads"], head_dim=cfg["head_dim"],
                intermediate_size=cfg["intermediate_size"], num_hidden_layers=2, rms_norm_eps=cfg["rms_norm_eps"],
                dflash_config=dict(mask_token_id=1000, target_layer_ids=[1, 3]), block_size=B)
    ctx = 96
    pos0 = 24
    g = D.DGeom(cfg, dcfg, ctx, B)
    md = QC.qwen_params(cfg)
    recs = D.step_program(g, md)
    if mutant == "no_mask_tail":
        recs = [r for r in recs if not r.tag.startswith("verify.mask_tail")]
    if mutant == "draft_causal":
        # the drafter's QK sees only the block rows up to the group's first slot (C.n = s0 + 1, not B): a causal
        # draft mask; the softmax then reads stale scores for the missing rows
        for r in recs:
            if r.tag.startswith("draft.qk.") and ".g" in r.tag:
                s0 = int(r.tag.split(".g")[1])
                r.desc["C"].n = s0 + 1
    image = encode_program(recs)
    assert encode_program(decode_program(image)) == image
    dr = Drafter(dcfg)
    gold = Gold(model, dr, g, pos0)
    init = gold.snapshot()
    M = build_machine(model, dr, g, gold, cfg)
    tok0 = 7
    ar = ar_decode(model, init, pos0, tok0, steps * B + 1)
    log(f"AR golden ({len(ar)} tokens): {ar[:24]}")
    pos, anchor, committed, out = pos0, tok0, [], []
    ok = True
    for st in range(steps):
        orc = None
        if st == oracle_step:
            n_done = len(committed)
            orc = ar[n_done:n_done + B - 1]
        t0 = time.time()
        try:
            tokx, dd = run_step(M, recs, image, anchor, pos, g, oracle=orc)
        except Fault as ex:
            out.append(dict(step=st, fault=str(ex)))
            return dict(B=B, pass_=False, steps=out, records=len(recs), image_bytes=len(image))
        wall = time.time() - t0
        gd, gp, gk = gold.step(pos, anchor, B, oracle=orc)
        st_rows = compare_state(M, g, gold, pos, model, dr)
        same_d = all(x == ([] if B == 1 else (orc[:B - 1] if orc is not None else gd[1:])) for x in dd)
        same_t = tokx == gp[:gk]
        ok_state = all(r["target_kv_rows"] and r["drafter_kv_rows"] and r["captured_features"] for r in st_rows)
        ok &= same_d and same_t and ok_state
        committed += tokx or []
        out.append(dict(step=st, pos=pos, anchor=anchor, oracle=orc is not None, k=len(tokx or []),
                        golden_k=gk, draft_ids_equal=same_d, committed_equal=same_t, state=st_rows,
                        tokens=tokx, wall_s=round(wall, 2)))
        log(f"B={B} step {st} pos {pos}: k {len(tokx or [])} (golden {gk}) draft==golden {same_d} "
            f"tokens==golden {same_t} state {ok_state} ({wall:.1f} s)")
        anchor, pos = tokx[-1], pos + len(tokx)
    lossless = committed == ar[:len(committed)]
    log(f"B={B} committed {len(committed)} tokens; equal to plain AR greedy: {lossless}")
    return dict(B=B, mutant=mutant, pass_=bool(ok and lossless), lossless_vs_ar=lossless, committed=committed,
                ar=ar[:len(committed)], steps=out, records=len(recs), image_bytes=len(image), ctx=ctx, pos0=pos0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--blocks", default="4,16")
    a = ap.parse_args()
    res = dict(schema="opentallas.hgi_sim.dflash_proof.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               what=__doc__.split("\n\n")[0], runs=[], mutants=[])
    for B in [int(x) for x in a.blocks.split(",")]:
        res["runs"].append(campaign(B, steps=3, oracle_step=1))
    for mu in ("no_mask_tail", "draft_causal"):
        r = campaign(16 if "16" in a.blocks else 4, steps=2, oracle_step=0, mutant=mu)
        res["mutants"].append(dict(mutant=mu, fails_as_required=not r["pass_"], detail=r["steps"][-1]))
        print("mutant", mu, "fails as required" if not r["pass_"] else "NOT DETECTED")
    res["pass"] = all(r["pass_"] for r in res["runs"]) and all(m["fails_as_required"] for m in res["mutants"])
    print("ALL PASS" if res["pass"] else "FAILURES")
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=1, default=str) + "\n")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
