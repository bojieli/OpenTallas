#!/usr/bin/env python3
"""LAYERBENCH-S81 (10-18, TOK.DS.BENCH.2): per-layer golden fixtures of the DeepSeek-V4.1 1M token for the S81-DV layer
bench, rebuilt from committed generators (the 10-13 hub-vehicle fixtures were on retired ot-epyc1tb).

Source of truth: the RELEASED checkpoint (DeepSeek-V4.1-Flash dba1be0a, rtl_v41_fullshape_layer_campaign.Checkpoint)
and the golden (tools/hdc_golden_v41.py, HDC_V41_ARITH=chunk8), at the w17 headline token (context 1,048,576, position
1,048,575, seed 20260930; the synthetic golden-consistent KV / index state and token history are the campaign's own
synthetic_state / token_history, one RNG stream per component and layer, so a layer is generated alone).

For one representative layer the tool re-runs the layer op by op with the golden's own arithmetic functions and records
the value at EVERY op boundary of the priced token DAG (results/arch/token_path_20261009/ds_rom.json op ids, the ids
tools/s81_dv/dv_layer_price.py prices and the layer compiler schedules).  Nothing is written unless the recorded run is
bit-exact against the pinned w17 golden shard (ctx1048576_L<L>.npz: attn_norm, attn, router, ffn_norm, ffn, engram,
index_scores, h_out, pre_out; head: logits): the op values are therefore the golden's, not a re-derivation.

Outputs (DIR):
  meta.json         layer, kind, token, experts, shard + checkpoint + source pins, checks, TP4 rank split of every op
  ops/<op>.bin      golden op-boundary values (little-endian raw; ops.json gives dtype / shape / sha256 / note)
  io/<k>.bin        h_in, pre_in, h_out, pre_out (the layer bench's entry / exit)
  state/<k>.bin     the KV / index / Engram images the die's HBM service reads (packed as the campaign's images():
                    FP8 E4M3 + UE8M0 window rows, FP4 E2M1 + E4M3/16 compressed rows, FP4 E2M1 + UE8M0/32 index keys
                    of THIS rank's contiguous quarter, open-group slots, Engram rows)          (--no-state: skipped)
  weights/<k>.bin   this rank's raw checkpoint slices of every matrix the layer reads (campaign die_slices split, the
                    input of the frame ROM image writer v41_die_images_w17w10 / frame_bench)    (--no-weights: skipped)
  manifest.sha256   sha256 of every file above (sha256sum format; deterministic: same inputs -> same bytes)

    HDC_V41_ARITH=chunk8 python3 tools/s81_dv/dv_layer_fixtures.py --layer L0 --out DIR [--rank 0]
    python3 tools/s81_dv/dv_layer_fixtures.py --verify DIR --manifest results/rtl/s81_layer_tput_1018/fixtures/L0.sha256.json

Layers: L0 (sliding), L2 (ratio2 + compressor + indexer), L14 (Engram + ratio2 + compressor + indexer), L20 (ratio1 +
compressor + indexer + candidates), HEAD (final hc_pre + norm + lm_head + argmax from the L39 shard), MTP (DSpark draft:
see GAPS in meta / the README; the w17 shard has no draft stage).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
F = np.float32
CTX = 1048576
SEED = 20260930
GOLD = Path(os.environ.get("OT_DSROM_1M_GOLD", "/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))
SCHEMA = "opentallas.s81_dv.layer_fixture.v1"
LAYERS = {"L0": 0, "L2": 2, "L14": 14, "L20": 20, "HEAD": 40, "MTP": None}
SOURCES = ["tools/s81_dv/dv_layer_fixtures.py", "tools/hdc_golden_v41.py", "tools/hdc_golden.py",
           "tools/rtl_v41_fullshape_layer_campaign.py", "compiler/models/deepseek-v4.1-flash/inference_config.json"]
TP = 4
TWO_HOP = (2,)          # layers whose priced DAG carries a second attn -> ffn sub-stage hop (ds_rom.json)


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def same(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        return False
    if a.dtype == np.float64 or b.dtype == np.float64:
        return bool(np.array_equal(a.astype(np.float64), b.astype(np.float64)))
    return bool(np.array_equal(np.asarray(a, F).view(np.uint32), np.asarray(b, F).view(np.uint32)))


# ---------------------------------------------------------------------------------------------- op recorder
class Rec:
    """op id -> value, in golden execution order (an op may hold several named parts: '<op>.<part>')."""

    def __init__(self):
        self.v = OrderedDict()
        self.note = {}

    def __call__(self, op, val, note=None):
        assert op not in self.v, f"op recorded twice: {op}"
        self.v[op] = val
        if note:
            self.note[op] = note
        return val


def _arr(v):
    if isinstance(v, (list, tuple)):
        v = np.asarray(v, dtype=np.int64)
    a = np.ascontiguousarray(np.asarray(v))
    if a.dtype == np.bool_:
        a = a.astype(np.uint8)
    if a.dtype not in (np.float32, np.float64, np.int64, np.uint8, np.int32, np.uint32):
        a = a.astype(F)
    return a


# ---------------------------------------------------------------------------------------------- golden pieces
def rms_parts(V, x, w, eps, rec, op):
    """rmsnorm_bf16 split at the DAG's op boundaries <op>.sumsq / .rsqrt / .scale (same expression, asserted)."""
    ss = rec(f"{op}.sumsq", V.split_sum(V.mul(x, x), V.RMS_SPLIT))
    r = rec(f"{op}.rsqrt", V.rsqrt(V.add(V.div(ss, F(len(x))), F(eps))))
    y = rec(f"{op}.scale", V.to_bf16(V.mul(w, V.mul(x, r))))
    assert same(y, V.rmsnorm_bf16(x, w, eps)), op
    return y


def hc_mixes(V, m, x, L, which, rec):
    """Model.hc_mixes with the DAG boundaries <which>.hc.sumsq / rsqrt / fn / pre_post / sinkhorn."""
    p = f"{which}.hc"
    fn, scale, base = (m.lw(L, f"hc_{which}_{s}") for s in ("fn", "scale", "base"))
    flat = x.reshape(-1)
    ss = rec(f"{p}.sumsq", V.split_sum(V.mul(flat, flat), V.HC_SS_SPLIT))
    r = rec(f"{p}.rsqrt", V.rsqrt(V.add(V.div(ss, F(flat.size)), m.eps)))
    raw = rec(f"{p}.fn", V.matvec_c(fn, flat, V.HC_SPLIT, cls="he"), "fn . flat (FP32, before the rsqrt scale)")
    mixes = V.mul(raw, r)
    h = m.hc
    pre = V.add(V.sigmoid(V.add(V.mul(mixes[:h], scale[0]), base[:h])), m.hc_eps)
    post = V.mul(V.sigmoid(V.add(V.mul(mixes[h:2 * h], scale[1]), base[h:2 * h])), F(2.0))
    rec(f"{p}.pre_post", np.concatenate([pre, post]), "pre[4] then post[4]")
    gp, gq, gc = m.hc_mixes(x, L, which)
    rec(f"{p}.sinkhorn", np.asarray(gc, F).reshape(-1), "comb[4x4] row-major (Model.hc_mixes, asserted pre / post)")
    assert same(gp, pre) and same(gq, post), p
    return gp, gq, gc


def engram(V, m, h, L, hist, rec):
    li = m.engram.layer_ids.index(L)
    ids = rec("eng.hash", m.engram.hashes(hist, li))
    rec("eng.lead_flit", np.asarray(hist[-m.engram.n:], np.int64), "transport: the token ids the hash reads")
    codes, sc = m.emb_codes[L]
    rows = rec("eng.hbm_read", V.decode_engram_rows(codes, sc, ids).reshape(-1), "decoded Engram rows (F32)")
    rec("eng.rows_allgather", rows, "transport: the gathered Engram rows (TP4 all-gather, same bits)")
    kv = rec("eng.wkv", V.linear_q(m.lw(L, "engram.wkv.weight"), rows))
    key = kv[:m.hc * m.dim].reshape(m.hc, m.dim)
    value = kv[m.hc * m.dim:]
    wgt = V.mul(m.lw(L, "engram.q_weight"), m.lw(L, "engram.k_weight"))
    out, kn, dots, gates = [], [], [], []
    for j in range(m.hc):
        hj, kj = h[j], key[j]
        n = F(m.dim)
        rh = V.rsqrt(V.add(V.div(V.reduce_sum_c(V.mul(hj, hj)), n), m.eps))
        rk = V.rsqrt(V.add(V.div(V.reduce_sum_c(V.mul(kj, kj)), n), m.eps))
        rstd = V.mul(rh, rk)
        kn.append([rh, rk])
        dot = V.mul(V.mul(V.reduce_sum_c(V.mul(V.mul(hj, wgt[j]), kj)), rstd), m.engram_scale)
        mag = V.sqrt(np.maximum(np.abs(dot), F(1e-6)).astype(F))
        gate = V.sigmoid(np.where(dot < 0, V.neg(mag), mag).astype(F))
        dots.append(dot)
        gates.append(gate)
        out.append(V.add(hj, V.mul(gate, value)))
    rec("eng.knorm", np.asarray(kn, F).reshape(-1), "per copy j: rsqrt(h_j), rsqrt(k_j)")
    rec("eng.dot", np.asarray(dots, F))
    rec("eng.gate", np.asarray(gates, F))
    hh = V.to_bf16(np.stack(out))
    rec("eng.add", hh)
    rec("eng.hh", hh, "transport: the Engram h the attention block reads (= eng.add)")
    assert same(hh, m.engram_layer(h.copy(), L, hist)), "engram"
    return hh


def indexer(V, m, L, x, qr, pos, st, ctx, rec):
    r, src = m.ratio[L], m.kv_of[L]
    n = (pos + 1) // r
    q = V.linear_q(m.lw(L, "attn.indexer.wq_b.weight"), qr).reshape(m.ih, m.ihd)
    q = V.rope_tail(q, V.rope_cs(m.freqs_yarn, pos))
    q = rec("attn.idx.q", np.stack([V.qdq_fp4_e8m0(q[h]) for h in range(m.ih)]))
    wts = rec("attn.idx.weights", V.to_bf16(V.mul(V.linear_bf16(m.lw(L, "attn.indexer.weights_proj.weight"), x),
                                                  m.index_w_scale)))
    keys = np.stack(st["ik"][src][:n])
    score = V.to_bf16(V.dots_q4(q, keys))
    terms = V.to_bf16(V.mul(np.maximum(score, F(0)), wts[:, None]))
    s = V.to_bf16(V.reduce_rows(terms.T, cls="idx")).astype(np.float64)
    if L == m.cand_src:
        ctx["cand"] = m.candidate_blocks(s, n)
        b = m.cand_b
        nb = -(-n // b)
        bs = np.concatenate([s, np.full(nb * b - n, -np.inf)]).reshape(nb, b).max(axis=1)
        rec("attn.cand.topk_local", bs, "block maxima (newest block pinned to +inf in cand.final)")
        rec("attn.cand.merge", ctx["cand"][::b], "kept blocks (top candidate_topk_blocks of the block maxima, newest "
                                                 "block pinned)")
        rec("attn.cand.final", ctx["cand"], "candidate mask over the n compressed positions")
    elif 0 <= m.cand_src < L:
        s = np.where(ctx["cand"][:n], s, -np.inf)
    rec("attn.idx.score", s, "index score per compressed position (BF16 values held as float64, -inf masked)")
    k = min(m.topk, n)
    sel = sorted(int(i) for i in V.topk_lowest_index(s, k))
    # the die's decomposition: each TP rank scores its contiguous quarter and keeps its local top-k; the merge of the
    # four local lists, ranked again, must give the golden selection exactly
    q4 = -(-n // TP)
    loc = [int(i) + rk * q4 for rk in range(TP) for i in V.topk_lowest_index(s[rk * q4:min(n, (rk + 1) * q4)], k)]
    rec("attn.idx.topk_local", np.asarray(loc, np.int64), f"rank-major local top-{k} of each rank's quarter ({q4})")
    cand = np.asarray(sorted(set(loc)), np.int64)
    merged = sorted(int(cand[i]) for i in V.topk_lowest_index(s[cand], k))
    assert merged == sel, "local top-k merge differs from the golden selection"
    rec("attn.idx.topk_merge", np.asarray(merged, np.int64))
    rec("attn.idx.topk_final", np.asarray(sel, np.int64), "ascending selected compressed positions")
    return sel


def compressor(V, m, L, x, pos, st, rec):
    r = m.ratio[L]
    if r == 1:
        raw = V.linear_bf16(m.lw(L, "attn.compressor.wkv.weight"), x)
        rec("attn.cmp.wkv", raw)
        return rms_parts(V, raw, m.lw(L, "attn.compressor.norm.weight"), m.eps, rec, "attn.cmp.norm")
    wkv = np.concatenate([m.lw(L, "attn.compressor.wkv.weight"), m.lw(L, "attn.compressor.wgate.weight")])
    kv, sc = np.split(V.mv(wkv, x), 2)
    rec("attn.cmp.wkv", np.concatenate([kv, sc]), "kv[512] then gate[512] (FP32)")
    slots = st["slots"][L]
    slots.append((kv, sc))
    st["slotrec"][L][pos] = (kv, sc)
    if (pos + 1) % r:
        return None
    st["slots"][L] = []
    kvs, scs = np.stack([a for a, _ in slots]), np.stack([b for _, b in slots])
    mx = np.max(scs, axis=0)
    e = V.exp(V.add(scs, V.neg(mx)))
    p = V.div(e, V.seqsum(list(e))[None, :])
    pooled = rec("attn.cmp.pool", V.seqsum([V.mul(kvs[i], p[i]) for i in range(r)]))
    return rms_parts(V, V.to_bf16(pooled), m.lw(L, "attn.compressor.norm.weight"), m.eps, rec, "attn.cmp.norm")


def attention(V, m, L, x, pos, st, ctx, rec):
    yarn = m.ratio[L] > 0
    cs = V.rope_cs(m.freqs_yarn if yarn else m.freqs_plain, pos)
    qa = V.linear_q(m.lw(L, "attn.wq_a.weight"), x)
    kraw = V.linear_q(m.lw(L, "attn.wkv.weight"), x)
    rec("attn.a_proj", np.concatenate([qa, kraw]), "wq_a out [1280] then wkv out [512] (BF16): one a_proj sweep")
    rec("attn.a_allgather", np.concatenate([qa, kraw]), "the gathered a_proj vector (TP4 all-gather, same bits)")
    qr = rms_parts(V, qa, m.lw(L, "attn.q_norm.weight"), m.eps, rec, "attn.q_norm")
    qq, qe = V.quant_fp8(qr)
    rec("attn.q_quant", np.concatenate([qq, qe.astype(np.float64)]), "E4M3 code values [1280] then block exps [40]")
    qb = rec("attn.wq_b", V.linear_q(m.lw(L, "attn.wq_b.weight"), qr))
    q = rec("attn.q_rope", V.rope_tail(qb.reshape(m.heads, m.hd), cs))
    kvn = rms_parts(V, kraw, m.lw(L, "attn.kv_norm.weight"), m.eps, rec, "attn.kv_norm")
    kv = rec("attn.kv_rope_qdq", V.qdq_fp8(V.rope_tail(kvn, cs)))
    rec("attn.own_row_write", kv, "the window row this position writes")
    st["win"][L].append(kv)
    rows = st["win"][L][-m.window:]
    rec("attn.window_load", np.stack(rows), f"window rows oldest first ({len(rows)} x {m.hd})")
    if yarn:
        src = m.kv_of[L]
        if L == src:
            latent = compressor(V, m, L, x, pos, st, rec)
            if latent is not None:
                r = m.ratio[L]
                gcs = V.rope_cs(m.freqs_yarn, pos + 1 - r)
                kr = V.linear_bf16(m.lw(L, "attn.indexer.wk.weight"), latent)
                rec("attn.cmp.wk", kr)
                k = rms_parts(V, kr, m.lw(L, "attn.indexer.k_norm.weight"), m.eps, rec, "attn.cmp.k_norm")
                ik = rec("attn.cmp.k_rope_qdq", V.qdq_fp4_e8m0(V.rope_tail(k, gcs)))
                rec("attn.idx.newkey", ik, "the index key appended this position")
                st["ik"][L].append(ik)
                st["ckv"][L].append(rec("attn.cmp.row_qdq", V.qdq_fp4_e4m3(V.rope_tail(latent, gcs), 16)))
        if L == m.idx_of[L]:
            ctx["sel"] = indexer(V, m, L, x, qr, pos, st, ctx, rec)
        g = [st["ckv"][src][i] for i in ctx["sel"]]
        rec("attn.gather", np.stack(g), f"selected compressed rows ({len(g)} x {m.hd})")
        rows = rows + g
        rec("attn.rows_allgather", np.stack(rows), "the attended rows (window then selections)")
    else:
        rec("attn.rows_allgather", np.stack(rows), "the attended rows (window)")
    kvm = np.stack(rows)
    assert not ("osm" in V.FUSE or m.vendor_decode_from is not None)
    return attend(V, m, L, q, kvm, cs, rec)


def attend(V, m, L, q, kvm, cs, rec):
    sink = m.lw(L, "attn.attn_sink")
    s = rec("attn.scores", V.mul(V.dots(q, kvm), m.attn_scale), "[heads, T] scaled scores (FP32)")
    mb = rec("attn.max", np.max(s, axis=1))
    e = rec("attn.exp", V.exp(V.add(s, V.neg(mb)[:, None])))
    pv = rec("attn.pv", V.dots(V.to_bf16(e), kvm.T), "[heads, hd] sum of bf16(P) x V (FP32)")
    es = rec("attn.den", V.reduce_rows(e))
    den = rec("attn.sink", V.add(es, V.exp(V.add(sink, V.neg(mb)))), "den + exp(sink - max)")
    o = rec("attn.normalize", V.to_bf16(V.div(pv, den[:, None])), "o (BF16, before the inverse RoPE)")
    o = V.rope_tail(o, cs, inverse=True)
    rec("attn.normalize.unrope", o, "o after the inverse RoPE (the wo_a operand)")
    og = o.reshape(m.groups, -1)
    wa = m.lw(L, "attn.wo_a.weight").reshape(m.groups, m.o_rank, -1)
    zz = np.stack([V.matvec_c(wa[g], og[g], V.WO_A_SPLIT) for g in range(m.groups)])
    zb = rec("attn.wo_a", V.to_bf16(zz.reshape(-1)))
    zq, ze = V.quant_fp8(zb)
    rec("attn.z_quant", np.concatenate([zq, ze.astype(np.float64)]), "E4M3 code values [8192] then block exps [256]")
    y = rec("attn.wo_b", V.linear_q(m.lw(L, "attn.wo_b.weight"), zb))
    rec("attn.out_allreduce", y, "the all-reduced wo_b output (canonical fold, same bits)")
    yy = m.attend(L, q, kvm, cs, None)
    assert same(yy, y), "attend"
    return y


def expert(V, m, prefix, x, weight, rec, tag):
    g = V.linear_q(m.w[prefix + "w1.weight"], x)
    u = V.linear_q(m.w[prefix + "w3.weight"], x)
    rec(f"{tag}.gu", np.concatenate([g, u]), "w1 (gate) out then w3 (up) out (BF16)")
    u = np.clip(u, -m.limit, m.limit).astype(F)
    g = np.minimum(g, m.limit).astype(F)
    a = V.mul(V.silu(g), u)
    rec(f"{tag}.swiglu", a)
    if weight is not None:
        a = V.mul(weight, a)
        rec(f"{tag}.route_w", a)
    ab = V.to_bf16(a)
    aq, ae = V.quant_fp8(ab)
    rec(f"{tag}.quant2", np.concatenate([aq, ae.astype(np.float64)]), "E4M3 code values then block exps")
    d = rec(f"{tag}.down", V.linear_q(m.w[prefix + "w2.weight"], ab))
    return d


def moe(V, m, L, x, rec):
    k_exp = m.k_exp if L < m.L else m.dspark_k_exp
    logit = rec("ffn.router", V.mv(m.lw(L, "ffn.gate.weight"), x), "gate . x (FP32)")
    scores = rec("ffn.softplus_sqrt", V.sqrt(V.softplus(logit)))
    rec("ffn.router_allgather", scores, "gathered router scores (TP4 all-gather, same bits)")
    biased = rec("ffn.bias", V.add(scores, m.lw(L, "ffn.gate.bias")))
    chosen = V.topk_lowest_index(biased, k_exp)
    rec("ffn.top6", np.asarray(chosen, np.int64), "rank order")
    ids = rec("ffn.top6_order", np.asarray(sorted(int(i) for i in chosen), np.int64), "ascending: run / sum order")
    total = V.seqsum([scores[i] for i in ids])
    den = V.add(total, F(1e-20))
    wts = [V.mul(V.div(scores[i], den), m.route_scale) for i in ids]
    rec("ffn.weights", np.asarray(wts, F), "routing weights in id order")
    y = np.zeros(m.dim, dtype=F)
    parts = []
    for j, i in enumerate(ids):
        d = expert(V, m, f"{m.P(L)}ffn.experts.{int(i)}.", x, wts[j], rec, f"ffn.experts.{int(i)}")
        parts.append(d)
        y = V.add(y, d)
    rec("ffn.experts_gu", np.concatenate([rec.v[f"ffn.experts.{int(i)}.gu"] for i in ids]), "all routed g,u (id order)")
    rec("ffn.swiglu", np.concatenate([rec.v[f"ffn.experts.{int(i)}.swiglu"] for i in ids]))
    rec("ffn.route_w", np.concatenate([rec.v[f"ffn.experts.{int(i)}.route_w"] for i in ids]))
    rec("ffn.quant2", np.concatenate([rec.v[f"ffn.experts.{int(i)}.quant2"] for i in ids]))
    rec("ffn.down", np.stack(parts), "routed down outputs (id order), summed sequentially from +0")
    sd = expert(V, m, f"{m.P(L)}ffn.shared_experts.", x, None, rec, "ffn.shared")
    rec.v["ffn.shared_gu"] = rec.v["ffn.shared.gu"]
    rec.v["ffn.shared_swiglu"] = rec.v["ffn.shared.swiglu"]
    rec.v["ffn.shared_quant"] = rec.v["ffn.shared.quant2"]
    y = V.to_bf16(V.add(y, sd))
    rec("ffn.combine_allreduce", y, "routed sum + shared, BF16 (the layer's ffn y)")
    return y, ids


def run_layer(V, m, L, cx, st, rec):
    h = cx["h"]
    pos = cx["pos"]
    if L in m.engram.layer_ids:
        h = engram(V, m, h, L, cx["hist"], rec)
    res = h
    a_pre, a_post, a_comb = hc_mixes(V, m, h, L, "attn", rec)
    xp = rec("attn.hc_pre", m.hc_pre(h, cx["pre"]))
    x = rms_parts(V, xp, m.lw(L, "attn_norm.weight"), m.eps, rec, "attn.norm")
    xq, xe = V.quant_fp8(x)
    rec("attn.quant", np.concatenate([xq, xe.astype(np.float64)]), "E4M3 code values [5120] then block exps [160]")
    y = attention(V, m, L, x, pos, st, cx, rec)
    h = rec("attn.hc_post", m.hc_post(y, res, a_post, a_comb))
    rec("substage_hop0", h, "transport: h crossing the attn -> ffn sub-stage hop")
    if L in TWO_HOP:
        rec("substage_hop1", h, "transport: the second sub-stage hop (same h)")
    out = {"attn_norm": x, "attn": y}
    res = h
    f_pre, f_post, f_comb = hc_mixes(V, m, h, L, "ffn", rec)
    xp = rec("ffn.hc_pre", m.hc_pre(h, a_pre))
    x = rms_parts(V, xp, m.lw(L, "ffn_norm.weight"), m.eps, rec, "ffn.norm")
    xq, xe = V.quant_fp8(x)
    rec("ffn.quant", np.concatenate([xq, xe.astype(np.float64)]), "E4M3 code values [5120] then block exps [160]")
    y, ids = moe(V, m, L, x, rec)
    h = rec("ffn.hc_post", m.hc_post(y, res, f_post, f_comb))
    out.update(ffn_norm=x, ffn=y, h_out=h, pre_out=np.asarray(f_pre, F), experts=[int(i) for i in ids],
               router=V.add(rec.v["ffn.softplus_sqrt"], m.lw(L, "ffn.gate.bias")))
    return out


# ---------------------------------------------------------------------------------------------- TP4 split metadata
def tp_split(m):
    """Rank r's share of every distributed op (the campaign die_slices split: output rows of every matrix in TP4
    contiguous quarters; wo_b by input columns (an all-reduce); h is 4 x 5120 on every rank; the DV die owns rows
    [320 g, 320 g + 320) of a 5,120 vector in slice g)."""
    q = lambda n: [[r * n // TP, (r + 1) * n // TP] for r in range(TP)]  # noqa: E731
    return {"a_proj.wq_a_rows": q(1280), "a_proj.wkv_rows": q(m.hd), "wq_b_rows": q(m.heads * m.hd),
            "heads": q(m.heads), "wo_a_rows": q(m.groups * m.o_rank), "wo_b_cols": q(m.groups * m.o_rank),
            "router_rows": q(m.n_exp), "expert_ff_rows": q(2304), "expert_down_rows": q(m.dim),
            "shared_ff_rows": q(2304), "index_keys": "rank-contiguous quarter of the compressed positions",
            "slice_rows": [[320 * g, 320 * g + 320] for g in range(16)]}


# ---------------------------------------------------------------------------------------------- writers
class Out:
    def __init__(self, d: Path):
        self.d = d
        self.files = OrderedDict()
        d.mkdir(parents=True, exist_ok=True)

    def put(self, rel, arr, **kw):
        a = _arr(arr)
        p = self.d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        b = a.tobytes()
        p.write_bytes(b)
        self.files[rel] = dict(dtype=str(a.dtype), shape=list(a.shape), sha256=sha_b(b), **kw)
        return self.files[rel]

    def text(self, rel, s):
        (self.d / rel).write_text(s)

    def manifest(self):
        lines = []
        for p in sorted(self.d.rglob("*")):
            if p.is_file() and p.name != "manifest.sha256":
                lines.append(f"{sha_b(p.read_bytes())}  {p.relative_to(self.d)}")
        (self.d / "manifest.sha256").write_text("\n".join(lines) + "\n")
        return lines


def src_pins():
    return {f: sha_b((ROOT / f).read_bytes()) for f in SOURCES if (ROOT / f).exists()}


def weights(LC, ck, m, L, rank, o, experts, eng):
    """The rank's raw checkpoint slices (the campaign's die_slices split)."""
    s = dict(tp=TP, dim=m.dim, hd=m.hd, heads=m.heads, q_rank=1280, o_groups=m.groups, o_rank=m.o_rank,
             n_exp=m.n_exp, moe_ff=2304, hc=m.hc, ratio=m.ratio)
    LC.R_KV_SRC, LC.R_IDX_SRC = (lambda: m.kv_src), (lambda: m.idx_src)
    for name, tensor, rows, cols in LC.die_slices(L, rank, s, experts, eng):
        a, dt = LC._raw(ck, tensor, rows, cols)
        o.put(f"weights/{name}.bin", a, tensor=tensor, rows=rows, cols=cols, format=dt)


def pack_fp8_exact(V, LC, rows):
    """Window rows (FP8 QDQ values) -> E4M3 codes + UE8M0 bytes, signed zero kept (code 0x80).  The campaign's
    pack_fp8_ue8m0 maps -0 and +0 to one code (np.unique merges them), so its round-trip assert fails on rows holding a
    -0 (L2 window); this packer takes the sign from the sign bit and the magnitude from the E4M3 table."""
    n, w = rows.shape
    v, e = LC._pow2_encode(rows, 32, 448.0, 3, -6)
    v = v.reshape(n, w)
    mag = {float(V.E4M3[i]): i for i in range(128) if np.isfinite(V.E4M3[i])}
    a = np.abs(v).reshape(-1)
    u, inv = np.unique(a, return_inverse=True)
    c = np.asarray([mag[float(t)] for t in u], np.uint8)[inv].reshape(n, w)
    c = c | (np.signbit(np.asarray(rows, F)).astype(np.uint8) << 7)
    eb = (e + 127).astype(np.uint8).reshape(n, w // 32)
    dec = (V.E4M3[c].reshape(-1, 32) * np.exp2(eb.reshape(-1).astype(np.int64) - 127)[:, None]).astype(F)
    assert np.array_equal(dec.reshape(n, w).view(np.uint32), np.asarray(rows, F).view(np.uint32)), "fp8 round trip"
    return c, eb


def state_images(V, LC, m, L, st, rank, o):
    win = np.stack(st["win"][L][:m.window - 1])
    c8, e8 = pack_fp8_exact(V, LC, win)
    o.put("state/kv.window.codes.bin", c8, format="F8_E4M3", rows=len(win), note="127 rows before this position")
    o.put("state/kv.window.scale.bin", e8, format="F8_E8M0")
    if m.ratio[L]:
        src = m.kv_of[L]
        n_pre = len(st["ckv"][src])
        ckv, ik = np.stack(st["ckv"][src]), np.stack(st["ik"][src])
        nib, sc = LC.pack_fp4_e4m3(ckv)
        o.put(f"state/kv.ckv{src}.codes.bin", nib, format="E2M1 packed (low nibble first)", rows=n_pre)
        o.put(f"state/kv.ckv{src}.scale.bin", sc, format="F8_E4M3 per 16")
        q4 = -(-len(ik) // TP)
        lo, hi = rank * q4, min(len(ik), (rank + 1) * q4)
        kn, ks = LC.pack_fp4_ue8m0(ik[lo:hi])
        o.put(f"state/kv.ik{src}.codes.bin", kn, format="E2M1 packed", rows=[lo, hi], note="this rank's quarter")
        o.put(f"state/kv.ik{src}.scale.bin", ks, format="F8_E8M0 per 32")
        if st["slots"].get(src):
            o.put(f"state/kv.slots{src}.bin", np.stack([np.stack(p) for p in st["slots"][src]]),
                  format="F32 (kv, gate) pairs of the open group")


# ---------------------------------------------------------------------------------------------- main
def gen_layer(a):
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    assert V.ARITH == "chunk8" and not V.FUSE, (V.ARITH, V.FUSE)
    L = LAYERS[a.layer]
    gaps = []
    o = Out(a.out)
    ck = LC.Checkpoint()
    if L == 40:
        return gen_head(a, V, LC, ck, o)
    if L is None:
        raise SystemExit("MTP: GAP -- the w17 1M shard has no DSpark draft stage (no golden op values to pin); "
                         "see results/rtl/s81_layer_tput_1018/fixtures/README.md")
    shard = GOLD / f"ctx{CTX}_L{L:02d}.npz"
    sj = json.loads((GOLD / f"ctx{CTX}_L{L:02d}.json").read_text())
    z = np.load(shard)
    eng = L in (1, 14)
    m, init_sha = LC.build_model(ck, engram=eng)
    st, sdesc = LC.synthetic_state(m, CTX, seed=SEED, layers=[L])
    hist = LC.token_history(CTX, seed=SEED)
    st["tokens"] = list(hist)
    cx = {"pos": CTX - 1, "hist": hist, "h": z["h_in"].astype(F), "pre": z["pre_in"].astype(F)}
    if (m.ratio[L] and m.idx_of[L] != L) or 0 <= m.cand_src < L:
        raise SystemExit(f"L{L} consumes a selection / candidate set carried from an earlier layer: not supported")
    if m.ratio[L] and m.kv_of[L] != L:
        raise SystemExit(f"L{L} reads KV source L{m.kv_of[L]} rows appended this token: not a representative layer")
    rec = Rec()
    # images of the state ENTERING the layer (before the layer appends its own rows)
    if not a.no_state:
        state_images(V, LC, m, L, st, a.rank, o)
    out = run_layer(V, m, L, cx, st, rec)
    checks = OrderedDict()
    checks["h_out_equals_shard"] = same(out["h_out"], z["h_out"])
    checks["pre_out_equals_shard"] = same(out["pre_out"], z["pre_out"])
    checks["block_equals_shard"] = same(out["h_out"], z[f"block{L}"])
    for k in ("attn_norm", "attn", "router", "ffn_norm", "ffn"):
        checks[f"{k}_equals_shard"] = same(out[k], z[f"L{L}.{k}"])
    if eng:
        checks["engram_equals_shard"] = same(rec.v["eng.add"], z[f"L{L}.engram"])
    if f"L{L}.index_scores" in z.files:
        checks["index_scores_equal_shard"] = same(rec.v["attn.idx.score"], z[f"L{L}.index_scores"])
    if f"win{L}" in z.files:
        checks["own_window_row_equals_shard"] = same(rec.v["attn.own_row_write"], z[f"win{L}"])
    if f"ckv{L}" in z.files:
        checks["ckv_row_equals_shard"] = same(rec.v["attn.cmp.row_qdq"], z[f"ckv{L}"])
        checks["ik_row_equals_shard"] = same(rec.v["attn.idx.newkey"], z[f"ik{L}"])
    checks["experts_equal_shard"] = out["experts"] == sj["experts"]
    print(json.dumps(checks, indent=1))
    if not all(checks.values()):
        raise SystemExit(f"L{L}: recorded op run is NOT bit-exact against the golden shard -- nothing published")
    ops = OrderedDict()
    for k, v in rec.v.items():
        ops[k] = o.put(f"ops/{k}.bin", v, note=rec.note.get(k))
    for k in ("h_in", "pre_in", "h_out", "pre_out"):
        o.put(f"io/{k}.bin", z[k])
    if not a.no_weights:
        weights(LC, ck, m, L, a.rank, o, out["experts"], eng)
    meta = OrderedDict(schema=SCHEMA, layer=a.layer, layer_index=L, kind=sj["kind"], context=CTX, position=CTX - 1,
                       seed=SEED, token=hist[-1], history=hist, rank=a.rank, tp=TP, experts=out["experts"],
                       arith=V.ARITH, fuse=sorted(V.FUSE), checks=checks,
                       shard=dict(path=str(shard), sha256=sha_b(shard.read_bytes()), input_sha256=sj["input_sha256"],
                                  output_sha256=sj["output_sha256"]),
                       checkpoint=str(LC.HF), golden_init_sha256=init_sha, state=sdesc, sources=src_pins(),
                       tp_split=tp_split(m), op_order=list(ops), gaps=gaps,
                       command=f"HDC_V41_ARITH=chunk8 python3 tools/s81_dv/dv_layer_fixtures.py --layer {a.layer} "
                               f"--rank {a.rank} --out DIR" + (" --no-state" if a.no_state else "")
                               + (" --no-weights" if a.no_weights else ""))
    o.text("ops.json", json.dumps(ops, indent=1) + "\n")
    o.text("files.json", json.dumps(o.files, indent=1) + "\n")
    o.text("meta.json", json.dumps(meta, indent=1, default=str) + "\n")
    lines = o.manifest()
    print(f"{a.out}: {len(lines)} files, {len(ops)} ops")
    if a.manifest_out:
        write_committed(a, meta, o, ops)


def gen_head(a, V, LC, ck, o):
    """HEAD: final hc_pre + norm + lm_head + argmax of the token, from the L39 shard exit h / pre."""
    z = np.load(GOLD / f"ctx{CTX}_L39.npz")
    zh = np.load(GOLD / f"ctx{CTX}_head.npz")
    m, init_sha = LC.build_model(ck, engram=False)
    rec = Rec()
    rec("head.hop", z["h_out"].astype(F), "transport: the L39 exit h reaching the head die")
    xp = rec("head.hc_pre", m.hc_pre(z["h_out"].astype(F), z["pre_out"].astype(F)))
    xf = rms_parts(V, xp, m.w["norm.weight"], m.eps, rec, "head.norm")
    logits = rec("head.lm_head", V.mv(m.w["head.weight"], xf), "[129280] FP32")
    v4 = -(-len(logits) // TP)
    loc = [int(np.argmax(logits[r * v4:(r + 1) * v4])) + r * v4 for r in range(TP)]
    rec("head.argmax", np.asarray(loc, np.int64), f"per-rank argmax over its vocab quarter ({v4})")
    nxt = rec("head.argmax_merge", np.asarray([loc[int(np.argmax([logits[i] for i in loc]))]], np.int64))
    rec("token.return", nxt, "transport: the next token returned to the embed stage")
    checks = OrderedDict(final_norm_equals_shard=same(xf, zh["xf"]), logits_equal_shard=same(logits, zh["logits"]),
                         next_token_equals_argmax=int(nxt[0]) == int(np.argmax(logits)))
    print(json.dumps(checks, indent=1))
    if not all(checks.values()):
        raise SystemExit("HEAD: not bit-exact against the golden head shard -- nothing published")
    ops = OrderedDict((k, o.put(f"ops/{k}.bin", v, note=rec.note.get(k))) for k, v in rec.v.items())
    o.put("io/h_in.bin", z["h_out"])
    o.put("io/pre_in.bin", z["pre_out"])
    o.put("io/next_token.bin", nxt)
    meta = OrderedDict(schema=SCHEMA, layer="HEAD", context=CTX, position=CTX - 1, seed=SEED, next_token=int(nxt[0]),
                       arith=V.ARITH, checks=checks, checkpoint=str(LC.HF), golden_init_sha256=init_sha,
                       shard=dict(path=str(GOLD / f"ctx{CTX}_head.npz"),
                                  sha256=sha_b((GOLD / f"ctx{CTX}_head.npz").read_bytes())),
                       sources=src_pins(), op_order=list(ops),
                       note="the vocabulary head (head.weight 129280 x 5120 BF16) runs on the separate head dies; "
                            "--weights packs the rank's vocab quarter",
                       command=f"HDC_V41_ARITH=chunk8 python3 tools/s81_dv/dv_layer_fixtures.py --layer HEAD --out DIR")
    if not a.no_weights:
        a0, a1 = a.rank * v4, min(len(logits), (a.rank + 1) * v4)
        w, dt = LC._raw(ck, "head.weight", (a0, a1), None)
        o.put("weights/head.bin", w, tensor="head.weight", rows=[a0, a1], format=dt)
        w, dt = LC._raw(ck, "norm.weight", None, None)
        o.put("weights/norm.bin", w, tensor="norm.weight", format=dt)
    o.text("ops.json", json.dumps(ops, indent=1) + "\n")
    o.text("files.json", json.dumps(o.files, indent=1) + "\n")
    o.text("meta.json", json.dumps(meta, indent=1, default=str) + "\n")
    o.manifest()
    if a.manifest_out:
        write_committed(a, meta, o, ops)


def write_committed(a, meta, o, ops):
    doc = OrderedDict(schema=SCHEMA + ".manifest", layer=a.layer, command=meta["command"], sources=meta["sources"],
                      shard=meta["shard"], checks=meta["checks"], experts=meta.get("experts"),
                      next_token=meta.get("next_token"), op_order=meta["op_order"],
                      bulk=a.bulk or "", files={k: v["sha256"] for k, v in o.files.items()},
                      meta_sha256=sha_b((o.d / "meta.json").read_bytes()),
                      ops={k: dict(shape=v["shape"], dtype=v["dtype"], sha256=v["sha256"]) for k, v in ops.items()})
    Path(a.manifest_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.manifest_out).write_text(json.dumps(doc, indent=1) + "\n")
    print("committed manifest", a.manifest_out)


def verify(a):
    doc = json.loads(Path(a.manifest).read_text())
    bad = []
    for rel, h in doc["files"].items():
        p = Path(a.verify) / rel
        if not p.exists() or sha_b(p.read_bytes()) != h:
            bad.append(rel)
    print(f"{len(doc['files']) - len(bad)} / {len(doc['files'])} files match {a.manifest}")
    for b in bad[:20]:
        print("MISMATCH", b)
    return 0 if not bad else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layer", choices=sorted(LAYERS))
    ap.add_argument("--out", type=Path)
    ap.add_argument("--rank", type=int, default=0)
    ap.add_argument("--no-state", action="store_true")
    ap.add_argument("--no-weights", action="store_true")
    ap.add_argument("--manifest-out", help="write the committed sha256 manifest here")
    ap.add_argument("--bulk", help="where the bulk copy lives (recorded in the manifest)")
    ap.add_argument("--verify", help="DIR to check against --manifest")
    ap.add_argument("--manifest")
    a = ap.parse_args(argv)
    if a.verify:
        return verify(a)
    assert a.layer and a.out, "--layer and --out"
    gen_layer(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
