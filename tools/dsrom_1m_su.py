#!/usr/bin/env python3
"""DeepSeek-V4.1 ROM (S81 baseline) at the 1M token: the vector / special-unit nodes of the per-layer graph measured in
RTL at the DS-ROM die's own geometry and TP4 per-die shapes, on real golden operands (minimum-component rule: one
die's stream unit per chain; the parent composes the token analytically).

The DS-ROM die's stream unit is the W11 SU element of the unified model's proposal preset (tools/uarch_model.py
PRESETS["spec_striped"] / "proposal": su_lanes 1,024, sfu_lanes 256), built as the W11 MEASURED serial build
(W11_SERIAL_MEASURED: MLAT 5 / ALAT 4, closes 1.111 ns SS = 0.9 GHz slow domain, AGENTS.md clock domains).  The bench
is rtl/hdc/v41x/ot_hdc_v41x_vec.sv on rtl/test/tb_hdc_v41x_vec.sv (tools/rtl_hdc_v41x_vec_campaign.py), driven by
tools/dshbm_baseline_measure.py's su-run (the same Chain lowering), with:

  unit   BCAST_STAGES 0 / RET_STAGES 0: the unit itself (its own controller accept, fetch, pipes, reducer);
  wired  BCAST_STAGES 22 / RET_STAGES 15: the plus-hub C_rotate network stages of the model's VMC_FUSED
         (FUSION_C_ROTATE_PLUS: control broadcast 6 + operand read 16 on the issue side, element write 15 on the
         return side) as RTL register stages on EVERY op (unfused upper bound; the reducer's result tree is 6 in
         the model, the bench charges RET 15 on results too).

Steps (golden on the host holding the released checkpoint; RTL on the compute host):
    python3 tools/dsrom_1m_su.py golden --out DIR            # replay L20/L00/L03/L24 + head at ctx 1,048,576
                                                             # (seed 20260930), capture every SU operand, check
                                                             # the layer outputs bit-exact against the w17 npz
    python3 tools/dsrom_1m_su.py prep   --out DIR            # lower the die-0 chains -> DIR/su_cases.pkl
    python3 tools/dsrom_1m_su.py check  --out DIR            # unit reference only (no RTL)
    python3 tools/dsrom_1m_su.py select --out DIR            # ot_hdc_select on the real router scores (top6 nodes)
    python3 tools/dsrom_1m_su.py run    --out DIR --variant unit|wired [--n 1024 --m 256 --fp dpi_beh]
    python3 tools/dsrom_1m_su.py equiv  --out DIR            # N64 rtl vs dpi_beh, same cases, MLAT5/ALAT4
    python3 tools/dsrom_1m_su.py record --out DIR --record results/rtl/dsrom_1m_allmeasured_20261004/su.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

F = np.float32
CTX = 1048576
SEED = 20260930
GOLD = Path(os.environ.get("OT_DSROM_1M_GOLD", "/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))
LAYERS = (20, 0, 3, 24)
TP, DIE = 4, 0
HEADS_DIE = 16                    # 64 heads / TP4
D = 5120
HC = 4
VOCAB_DIE = 129280 // TP          # lm_head vocabulary split 4 ways: 32,320 logits a die
SLOW_HZ, FAST_HZ = 0.9e9, 1.2e9
MLAT, ALAT = 5, 4                 # uarch_model.W11_SERIAL_MEASURED (mlat 5, alat 4)
VARIANTS = {"unit": (0, 0), "wired": (6 + 16, 15)}   # FUSION_C_ROTATE_PLUS: bcast 6 + read 16 | write 15


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def bits(x):
    return np.asarray(x, dtype=F).view(np.uint32)


def same(a, b):
    return bool(np.array_equal(bits(a).reshape(-1), bits(b).reshape(-1)))


# ======================================================================================================================
# golden: replay the layers with every SU operand captured
# ======================================================================================================================
def _replay(m, L, st, cx, V):
    """Run m.layer(L) with the golden's own module functions logged and the hyper-connection / attention core /
    expert steps replicated verbatim (their replicas' results are what the layer uses, so the layer output's
    bit-exact match with the recorded shard proves every captured operand is the golden's)."""
    names = ["linear_q", "linear_bf16", "rmsnorm_bf16", "rope_tail", "mv", "qdq_fp8", "qdq_fp4_e8m0", "qdq_fp4_e4m3"]
    orig = {n: getattr(V, n) for n in names}
    log = []

    def keep(x):          # references (the golden builds new arrays; weights keep their identity for _pick)
        return x

    def wrap(n):
        f = orig[n]

        def g(*args, **kw):
            r = f(*args, **kw)
            log.append(dict(fn=n, args=tuple(keep(a) for a in args), kw=dict(kw), out=keep(r)))
            return r
        return g

    cap = {}
    hc_orig, attend_orig, expert_orig = m.hc_mixes, m.attend, m.expert

    def hc_mixes(x, L_, which):
        fn, scale, base = (m.lw(L_, f"hc_{which}_{s}") for s in ("fn", "scale", "base"))
        flat = x.reshape(-1)
        assert np.array_equal(V.to_bf16(flat), flat)
        ss = V.split_sum(V.mul(flat, flat), V.HC_SS_SPLIT)
        r = V.rsqrt(V.add(V.div(ss, F(flat.size)), m.eps))
        raw = V.matvec_c(fn, flat, V.HC_SPLIT, cls="he")
        mixes = V.mul(raw, r)
        h = m.hc
        pre = V.add(V.sigmoid(V.add(V.mul(mixes[:h], scale[0]), base[:h])), m.hc_eps)
        post = V.mul(V.sigmoid(V.add(V.mul(mixes[h:2 * h], scale[1]), base[h:2 * h])), F(2.0))
        comb0 = V.add(V.mul(mixes[2 * h:], scale[2]), base[2 * h:]).reshape(h, h)
        mx = np.max(comb0, axis=1, keepdims=True)
        e = V.exp(V.add(comb0, V.neg(mx)))
        rs = V.seqsum([e[:, k] for k in range(h)])
        comb = V.add(V.div(e, rs[:, None]), m.hc_eps)

        def cols(cm):
            cs = V.seqsum([cm[j, :] for j in range(h)])
            return V.div(cm, V.add(cs, m.hc_eps)[None, :])

        def rows(cm):
            rs_ = V.seqsum([cm[:, k] for k in range(h)])
            return V.div(cm, V.add(rs_, m.hc_eps)[:, None])
        comb = cols(comb)
        for _ in range(m.sinkhorn_iters - 1):
            comb = cols(rows(comb))
        cap[f"hc.{which}"] = dict(x=x.copy(), ss=F(ss), r=F(r), raw=raw.copy(), scale=np.asarray(scale, F).copy(),
                                  base=np.asarray(base, F).copy(), pre=pre, post=post, comb0=comb0, max=mx.reshape(-1),
                                  e=e, comb=comb)
        return pre, post, comb

    def attend(L_, q, kvm, cs, blocks=None):
        assert blocks is None or (len(blocks) == 1 and len(blocks[0]) == len(kvm)), "single-block softmax only"
        sink = m.lw(L_, "attn.attn_sink")
        s_raw = V.dots(q, kvm)
        s = V.mul(s_raw, m.attn_scale)
        mb = np.max(s, axis=1)
        e = V.exp(V.add(s, V.neg(mb)[:, None]))
        pv = V.dots(V.to_bf16(e), kvm.T)
        es = V.reduce_rows(e)
        den = V.add(es, V.exp(V.add(sink, V.neg(mb))))
        o0 = V.to_bf16(V.div(pv, den[:, None]))
        o = orig["rope_tail"](o0, cs, inverse=True)
        og = o.reshape(m.groups, -1)
        wa = m.lw(L_, "attn.wo_a.weight").reshape(m.groups, m.o_rank, -1)
        z = np.stack([V.matvec_c(wa[g], og[g], V.WO_A_SPLIT) for g in range(m.groups)])
        z = V.to_bf16(z.reshape(-1))
        H = HEADS_DIE
        cap["attend"] = dict(q=q[:H].copy(), T=int(len(kvm)), s_raw=s_raw[:H].copy(), s=s[:H].copy(), max=mb[:H].copy(),
                             e=e[:H].copy(), es=es[:H].copy(), sink=np.asarray(sink, F)[:H].copy(), den=den[:H].copy(),
                             pv=pv[:H].copy(), o0=o0[:H].copy(), o=o[:H].copy(), cs=cs, attn_scale=F(m.attn_scale),
                             z=z.copy())
        return V.linear_q(m.lw(L_, "attn.wo_b.weight"), z)

    def expert(prefix, x, weight=None):
        g0 = V.linear_q(m.w[prefix + "w1.weight"], x)
        u0 = V.linear_q(m.w[prefix + "w3.weight"], x)
        u = np.clip(u0, -m.limit, m.limit).astype(F)
        g = np.minimum(g0, m.limit).astype(F)
        a = V.mul(V.silu(g), u)
        if weight is not None:
            a = V.mul(weight, a)
        cap.setdefault("experts", []).append(dict(prefix=prefix, g=g0.copy(), u=u0.copy(),
                                                   weight=None if weight is None else F(weight), a=V.to_bf16(a)))
        return V.linear_q(m.w[prefix + "w2.weight"], V.to_bf16(a))

    hcp_orig, hcpost_orig = m.hc_pre, m.hc_post

    def hc_pre(x, pre):
        out = hcp_orig(x, pre)
        cap.setdefault("hc_pre", []).append(dict(h=x.copy(), pre=np.asarray(pre, F).copy(), out=out.copy()))
        return out

    def hc_post(y, res, post, comb):
        out = hcpost_orig(y, res, post, comb)
        cap.setdefault("hc_post", []).append(dict(y=np.asarray(y, F).copy(), res=res.copy(), post=post.copy(),
                                                  comb=comb.copy(), out=out.copy()))
        return out

    for n in names:
        setattr(V, n, wrap(n))
    m.hc_mixes, m.attend, m.expert, m.hc_pre, m.hc_post = hc_mixes, attend, expert, hc_pre, hc_post
    tr = {}
    try:
        m.layer(L, cx, st, tr)
    finally:
        for n in names:
            setattr(V, n, orig[n])
        for k in ("hc_mixes", "attend", "expert", "hc_pre", "hc_post"):
            delattr(m, k)
    return cap, log, tr


def _pick(log, fn, pred=lambda e: True):
    hits = [e for e in log if e["fn"] == fn and pred(e)]
    return hits


def cmd_golden(a):
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    layers = [int(x) for x in a.layers.split(",")] if a.layers else list(LAYERS)
    ck = LC.Checkpoint()
    m, init_sha = LC.build_model(ck, engram=False)
    summary = {}
    for L in layers:
        t0 = time.time()
        z = np.load(GOLD / f"ctx{CTX}_L{L:02d}.npz")
        js = json.loads((GOLD / f"ctx{CTX}_L{L:02d}.json").read_text())
        st, sdesc = LC.synthetic_state(m, CTX, seed=SEED, layers=[L])
        src = m.kv_of.get(L)
        if src is not None and src < L:          # the source layer ran earlier this token: its new rows
            zs = np.load(GOLD / f"ctx{CTX}_L{src:02d}.npz")
            if f"ckv{src}" in zs.files:
                st["ckv"][src].append(zs[f"ckv{src}"])
                st["ik"][src].append(zs[f"ik{src}"])
        hist = json.loads((GOLD / f"golden_ctx{CTX}_0-39.json").read_text())["history"]
        st["tokens"] = list(hist)
        cx = {"pos": CTX - 1, "hist": hist, "h": z["h_in"].copy(), "pre": z["pre_in"].copy()}
        if L > 0:
            carry = json.loads((GOLD / f"ctx{CTX}_L{L - 1:02d}.json").read_text())["ctx_out"]
            if "sel" in carry:
                cx["sel"] = carry["sel"]
            if "cand_file" in carry:
                cx["cand"] = np.load(GOLD / carry["cand_file"])["cand"]
        assert LC.digest(cx["h"], cx["pre"]) == js["input_sha256"]
        cap, log, tr = _replay(m, L, st, cx, V)
        ok = dict(h_out=same(cx["h"], z["h_out"]), pre_out=same(cx["pre"], z["pre_out"]),
                  **{k: same(tr[k], z[k]) for k in (f"L{L}.attn_norm", f"L{L}.attn", f"L{L}.router",
                                                     f"L{L}.ffn_norm", f"L{L}.ffn") if k in z.files})
        # ---- the attention front's operands, from the logged golden calls
        lw = lambda n: m.lw(L, n)                                                      # noqa: E731
        rq = _pick(log, "rmsnorm_bf16", lambda e: e["args"][1] is lw("attn.q_norm.weight"))
        rkv = _pick(log, "rmsnorm_bf16", lambda e: e["args"][1] is lw("attn.kv_norm.weight"))
        ropes = _pick(log, "rope_tail", lambda e: not e["kw"].get("inverse", False))
        yarn = m.ratio[L] > 0
        q_rope = [e for e in ropes if np.asarray(e["args"][0]).shape == (m.heads, m.hd)]
        kv_rope = [e for e in ropes if np.asarray(e["args"][0]).shape == (m.hd,)]
        rec = dict(layer=L, kind=js["kind"], T=cap["attend"]["T"], checks=ok,
                   eps=F(m.eps), hc_eps=F(m.hc_eps), route_scale=F(m.route_scale), limit=F(m.limit),
                   hc=cap, attn_norm_w=np.asarray(lw("attn_norm.weight"), F), ffn_norm_w=np.asarray(lw("ffn_norm.weight"), F),
                   q_norm=dict(x=rq[0]["args"][0], w=np.asarray(lw("attn.q_norm.weight"), F), out=rq[0]["out"]),
                   kv_norm=dict(x=rkv[0]["args"][0], w=np.asarray(lw("attn.kv_norm.weight"), F), out=rkv[0]["out"]),
                   q_rope=dict(x=np.asarray(q_rope[0]["args"][0])[:HEADS_DIE].copy(), cs=q_rope[0]["args"][1],
                               out=np.asarray(q_rope[0]["out"])[:HEADS_DIE].copy()),
                   kv_rope=dict(x=kv_rope[0]["args"][0], cs=kv_rope[0]["args"][1], out=kv_rope[0]["out"]))
        if L in m.kv_src and yarn:
            rc = _pick(log, "rmsnorm_bf16", lambda e: e["args"][1] is lw("attn.compressor.norm.weight"))
            rk = _pick(log, "rmsnorm_bf16", lambda e: e["args"][1] is lw("attn.indexer.k_norm.weight"))
            krope = [e for e in ropes if np.asarray(e["args"][0]).shape == (m.ihd,)]
            rec["cmp"] = dict(norm=dict(x=rc[-1]["args"][0], w=np.asarray(lw("attn.compressor.norm.weight"), F),
                                        out=rc[-1]["out"]),
                              k_norm=dict(x=rk[0]["args"][0], w=np.asarray(lw("attn.indexer.k_norm.weight"), F),
                                          out=rk[0]["out"]),
                              k_rope=dict(x=krope[0]["args"][0], cs=krope[0]["args"][1], out=krope[0]["out"]),
                              row_rope=dict(x=kv_rope[1]["args"][0], cs=kv_rope[1]["args"][1], out=kv_rope[1]["out"]))
        if yarn and L == m.idx_of[L]:
            iq = [e for e in ropes if np.asarray(e["args"][0]).shape == (m.ih, m.ihd)]
            rec["idx_q"] = dict(x=iq[0]["args"][0], cs=iq[0]["args"][1], out=iq[0]["out"])
        # ---- the router and the experts
        gate = _pick(log, "mv", lambda e: e["args"][0] is lw("ffn.gate.weight"))
        raw = gate[0]["out"]
        scores = V.sqrt(V.softplus(raw))
        bias = np.asarray(lw("ffn.gate.bias"), F)
        ids = sorted(int(i) for i in V.topk_lowest_index(V.add(scores, bias), m.k_exp))
        tot = V.seqsum([scores[i] for i in ids])
        den = V.add(tot, F(1e-20))
        wts = np.asarray([V.mul(V.div(scores[i], den), m.route_scale) for i in ids], F)
        ok["router_recomputed"] = same(V.add(scores, bias), z[f"L{L}.router"])
        ok["experts"] = ids == js["experts"]
        rec["router"] = dict(raw=raw, scores=scores, bias=bias, biased=V.add(scores, bias), ids=ids, weights=wts)
        rec["experts"] = cap["experts"]
        rec["checks"] = ok
        (out / f"snap_L{L:02d}.pkl").write_bytes(pickle.dumps(rec))
        summary[f"L{L}"] = dict(kind=js["kind"], T=rec["T"], checks=ok, wall_s=round(time.time() - t0, 1),
                                state_sha256=sdesc["state_sha256"])
        print(f"L{L:02d} {js['kind']} T {rec['T']} checks {ok} {time.time() - t0:.0f} s", flush=True)
        for k in [k for k in m.w if k.startswith(f"layers.{L}.")]:
            del m.w[k]
        del st
    # ---- head: final hc_pre + norm on the last layer's output, the die's logits
    z39 = np.load(GOLD / f"ctx{CTX}_L39.npz")
    zh = np.load(GOLD / f"ctx{CTX}_head.npz")
    xf = V.rmsnorm_fold(m.hc_pre(z39["h_out"], z39["pre_out"]), m.w["norm.weight"], m.eps)
    head = dict(h=z39["h_out"], pre=z39["pre_out"], w=np.asarray(m.w["norm.weight"], F), eps=F(m.eps), xf=xf,
                logits=zh["logits"], checks=dict(xf=same(xf, zh["xf"])))
    (out / "snap_head.pkl").write_bytes(pickle.dumps(head))
    summary["head"] = dict(checks=head["checks"])
    print("head", head["checks"], flush=True)
    prev = out / "golden.json"
    if prev.exists():                            # merge earlier invocations' layers
        for k, v in json.loads(prev.read_text())["layers"].items():
            summary.setdefault(k, v)
    gsum = dict(schema="opentallas.dsrom.1m_su_golden.v1", generated_utc=now(), source_commit=git_head(),
                context=CTX, seed=SEED, gold_dir=str(GOLD), arith=V.ARITH, fuse=sorted(V.FUSE),
                golden_sha256={p: sha(ROOT / p) for p in ("tools/hdc_golden_v41.py", "tools/hdc_golden.py")},
                golden_init_sha256=init_sha, layers=summary,
                status="pass" if all(all(v["checks"].values()) for v in summary.values()) else "fail")
    (out / "golden.json").write_text(json.dumps(gsum, indent=1, default=str) + "\n")
    print("GOLDEN", gsum["status"])
    return 0 if gsum["status"] == "pass" else 1


# ======================================================================================================================
# prep: the die-0 chains at the DS-ROM TP4 shapes
# ======================================================================================================================
def f32u(x):
    return int(np.asarray(F(x)).view(np.uint32))


def chain_hc_mix(B, VC, I, c, hc):
    """attn|ffn.hc.{sumsq, rsqrt, pre_post} + the Sinkhorn unit's front (row max, exp).  The [24, 20480] mixes
    matvec (hc.fn) is the field's, not the SU's: its raw output is a VM operand here."""
    x = hc["x"].reshape(-1)
    n = len(x)
    X = c.vm(x)
    SS = c.buf(8)
    c.op(nout=8, nin=n // 8, abase=X, aso=n // 8, asi=1, red=I.RED_SUM, redsq=1, redtree=1, rbase=SS, dst=0)  # 0
    R = c.buf(8)
    c.op(nout=1, nin=1, abase=SS, m1=I.M1_DIVIMM, imm1=f32u(n), ad=I.AD_IMM, imm2=f32u(c.eps), sfu=I.SFU_RSQRT,
         obase=R)                                                                                              # 1
    c.check("hc rstd", R, [hc["r"]])
    RAW = c.vm(hc["raw"])
    base = c.crom(hc["base"])
    PRE, POST, CMB = c.buf(8), c.buf(8), c.buf(16)
    c.op(nout=1, nin=4, abase=RAW, aso=4, asi=1, bbase=R, m1=I.M1_AB, m2=I.M2_IMM, imm1=f32u(hc["scale"][0]),
         csrc=I.SRC_CLO, cbase=base, cso=4, csi=1, ad=I.AD_C, sfu=I.SFU_SIGM, e1=I.E1_ADDIMM, imm2=f32u(c.hc_eps),
         obase=PRE, oso=4, osi=1)                                                                              # 2
    c.op(nout=1, nin=4, abase=RAW + 4, aso=4, asi=1, bbase=R, m1=I.M1_AB, m2=I.M2_IMM, imm1=f32u(hc["scale"][1]),
         csrc=I.SRC_CLO, cbase=base + 4, cso=4, csi=1, ad=I.AD_C, sfu=I.SFU_SIGM, e1=I.E1_MULIMM, imm2=f32u(2.0),
         obase=POST, oso=4, osi=1)                                                                             # 3
    c.op(nout=1, nin=16, abase=RAW + 8, aso=16, asi=1, bbase=R, m1=I.M1_AB, m2=I.M2_IMM, imm1=f32u(hc["scale"][2]),
         csrc=I.SRC_CLO, cbase=base + 8, cso=16, csi=1, ad=I.AD_C, obase=CMB, oso=16, osi=1)                   # 4
    c.check("pre", PRE, hc["pre"])
    c.check("post", POST, hc["post"])
    c.check("comb (before softmax)", CMB, hc["comb0"].reshape(-1))
    MX = c.buf(8)
    c.op(nout=4, nin=4, abase=CMB, aso=4, asi=1, red=I.RED_MAX, rbase=MX, rso=1, dst=0)                        # 5
    E = c.buf(16)
    c.op(nout=4, nin=4, abase=CMB, aso=4, asi=1, bbase=MX, bso=1, bsi=0, ad=I.AD_NEGB, sfu=I.SFU_EXP,
         obase=E, oso=4, osi=1)                                                                                # 6
    c.check("row max", MX, hc["max"])
    c.check("exp(comb - max): the Sinkhorn unit's input", E, hc["e"].reshape(-1))
    return [("hc.sumsq", 0, "result"), ("hc.rsqrt", 1, "write"), ("hc.pre_post", 4, "write"),
            ("hc.sinkhorn:front", 6, "write")]


def chain_hc_pre_norm(B, VC, I, c, h, pre, w, want):
    """hc_pre (collapse the 4 copies with the pending pre mix) + RMSNorm (sumsq fused into the third mix op)."""
    y = B.lower_hc_pre_norm(c, I, h, pre, np.asarray(w, F), c.eps)
    c.check("x (normed)", y, want)
    return [("hc_pre", 2, "write"), ("norm.sumsq", 2, "result"), ("norm.rsqrt", 3, "write"), ("norm.scale", 4, "write")]


def chain_rmsnorm(B, VC, I, c, d, prefix):
    y = B.lower_rmsnorm(c, I, c.vm(d["x"]), len(d["x"]), np.asarray(d["w"], F), c.eps)
    c.check(f"{prefix} out", y, d["out"])
    return y, [(f"{prefix}.sumsq", 0, "result"), (f"{prefix}.rsqrt", 1, "write"), (f"{prefix}.scale", 2, "write")]


def lower_rope_rows(c, I, xa, rows, width, cs, out=None, inverse=False):
    """RoPE of the last 2*len(cos) elements of `rows` rows of `width` at xa (row stride width), one op, the tails
    written to `out` (rows x rd, packed) or in place; inverse: the conjugate (QM_ALT_PN)."""
    cos, sin = cs
    rd = 2 * len(cos)
    tb = c.crom(cos, sin)
    t0 = xa + width - rd
    assert t0 % 2 == 0 and width % 2 == 0
    if out is None:
        out, oso = t0, width
    else:
        oso = rd
    c.op(nout=rows, nin=rd, abase=t0, aso=width, asi=1, cpair=1, bsrc=I.SRC_CLO, bbase=tb, bso=0, bsi=1, bhalf=1,
         dsrc=I.SRC_CHI, dbase=tb, dso=0, dsi=1, m1=I.M1_AB, qm=I.QM_ALT_PN if inverse else I.QM_ALT_NP, ad=I.AD_Q,
         rnd=1, obase=out, oso=oso, osi=1)
    return out


def chain_attend(B, VC, I, c, at):
    """Softmax over T rows for the die's 16 heads (scale + row max, exp + row sum, sink + denominator), the
    normalisation acc/den (BF16) and the inverse RoPE.  q.k (attn.scores) and P.V (attn.pv) are the attention
    tile's (their FP32 results are VM operands here)."""
    H, T = at["s_raw"].shape
    S0 = c.vm(at["s_raw"])
    S = c.buf(H * T)
    MB = c.buf(H)
    c.op(nout=H, nin=T, abase=S0, aso=T, asi=1, m1=I.M1_AIMM, imm1=f32u(at["attn_scale"]), obase=S, oso=T, osi=1,
         red=I.RED_MAX, rbase=MB, rso=1)                                                                      # 0
    c.check("scaled scores", S, at["s"])
    c.check("row max", MB, at["max"])
    E = c.buf(H * T)
    SE = c.buf(H)
    c.op(nout=H, nin=T, abase=S, aso=T, asi=1, bbase=MB, bso=1, bsi=0, ad=I.AD_NEGB, sfu=I.SFU_EXP, obase=E, oso=T,
         osi=1, red=I.RED_SUM, rbase=SE, rso=1)                                                               # 1
    c.check("exp(s - max) (P before BF16, the tile's P.V input)", E, at["e"])
    c.check("row sum", SE, at["es"])
    SK = c.vm(at["sink"])
    DEN = c.buf(H)
    c.op(nout=H, nin=1, abase=SK, aso=1, asi=1, bbase=MB, bso=1, bsi=0, ad=I.AD_NEGB, sfu=I.SFU_EXP, e1=I.E1_ADDC,
         cbase=SE, cso=1, csi=1, obase=DEN, oso=1, osi=1)                                                      # 2
    c.check("denominator (row sum + exp(sink - max))", DEN, at["den"])
    PV = c.vm(at["pv"])
    O = c.buf(H * 512)
    c.op(nout=H, nin=512, abase=PV, aso=512, asi=1, bbase=DEN, bso=1, bsi=0, m1=I.M1_DIVB, rnd=1, obase=O, oso=512,
         osi=1)                                                                                                # 3
    # (acc / den is checked through o: the inverse RoPE below rewrites the tails in place)
    lower_rope_rows(c, I, O, H, 512, at["cs"], inverse=True)                                                   # 4
    c.check("o (inverse RoPE): wo_a's input", O, at["o"])
    return [("max", 0, "result"), ("exp", 1, "write"), ("den", 1, "result"), ("sink", 2, "write"),
            ("normalize", 4, "write")]


def chain_hc_post(B, VC, I, c, hp):
    o = B.lower_hc_post(c, I, hp["y"], hp["res"], hp["post"], hp["comb"])
    c.check("h (hc_post)", o, hp["out"])
    return [("hc_post", 3, "write")]


def chain_router_act(B, VC, I, c, rt):
    n = len(rt["raw"]) // TP
    g = rt["raw"][DIE * n:(DIE + 1) * n]
    ga = c.vm(g)
    o = c.buf(n)
    c.op(nout=1, nin=n, abase=ga, aso=n, asi=1, sfu=I.SFU_SPSQRT, obase=o, oso=n, osi=1)
    c.check(f"sqrt(softplus) of the die's {n} router rows", o, rt["scores"][DIE * n:(DIE + 1) * n])
    return [("ffn.softplus_sqrt", 0, "write")]


def chain_route(B, VC, I, c, rt, route_scale):
    S_ = c.vm(rt["scores"])
    bias = c.crom(rt["bias"])
    BI = c.buf(384)
    c.op(nout=1, nin=384, abase=S_, aso=384, asi=1, csrc=I.SRC_CLO, cbase=bias, cso=384, csi=1, ad=I.AD_C, obase=BI,
         oso=384, osi=1)                                                                                       # 0
    c.check("scores + bias (the select's input)", BI, rt["biased"])
    IX = c.vm_u32(np.asarray(rt["ids"], np.uint32))      # the top-6 itself: ot_hdc_select (cmd select)
    TOT = c.buf(8)
    c.op(nout=1, nin=6, abase=S_, asi=1, aso=6, aind=I.IND_I, aibase=IX, red=I.RED_SUM, redwhole=1, rbase=TOT,
         dst=0)                                                                                                # 1
    DEN = c.buf(8)
    c.op(nout=1, nin=1, abase=TOT, ad=I.AD_IMM, imm2=f32u(1e-20), obase=DEN)                                   # 2
    W = c.buf(8)
    c.op(nout=1, nin=6, abase=S_, asi=1, aso=6, aind=I.IND_I, aibase=IX, bbase=DEN, m1=I.M1_DIVB,
         e1=I.E1_MULIMM, imm2=f32u(route_scale), obase=W, oso=6, osi=1)                                        # 3
    c.check("route weights", W, rt["weights"])
    return [("ffn.bias", 0, "write"), ("ffn.weights", 3, "write")]


def chain_swiglu(B, VC, I, c, experts, limit, routed=True):
    """The die's 1/4 of the intermediate rows (2,304 / 4 = 576) of the 6 routed experts (one op, the routing weight
    fused as E2) or of the shared expert."""
    ex = [e for e in experts if (e["weight"] is not None) == routed]
    rows = 2304 // TP
    lo, hi = DIE * rows, (DIE + 1) * rows
    g = np.concatenate([e["g"][lo:hi] for e in ex])
    u = np.concatenate([e["u"][lo:hi] for e in ex])
    want = np.concatenate([e["a"][lo:hi] for e in ex])
    ne = len(ex)
    ga, ua = c.vm(g), c.vm(u)
    o = c.buf(ne * rows)
    kw = dict(nout=ne, nin=rows, abase=ga, aso=rows, asi=1, amin=1, imm3=f32u(limit), sfu=I.SFU_SILU, cbase=ua,
              cso=rows, csi=1, cclip=1, e1=I.E1_MULC, rnd=1, obase=o, oso=rows, osi=1)
    if routed:
        W = c.vm(np.asarray([e["weight"] for e in ex], F))
        kw.update(bbase=W, bso=1, bsi=0, e2=I.E2_MULB)
    c.op(**kw)
    c.check(("routed x6" if routed else "shared") + " swiglu (x route weight), BF16", o, want)
    return [("ffn.swiglu" if routed else "ffn.shared_swiglu", 0, "write")]


def chain_route_w(B, VC, I, c, experts, limit):
    """ffn.route_w as its own SU op (the graph's node): x routing weight on the FP32 silu(g) * u of the die's 576
    rows of each of the 6 routed experts, BF16 out (the w2 input).  The shared expert carries no routing weight."""
    import hdc_golden_v41 as V
    ex = [e for e in experts if e["weight"] is not None]
    rows = 2304 // TP
    lo, hi = DIE * rows, (DIE + 1) * rows
    prod = []
    for e in ex:
        u = np.clip(e["u"][lo:hi], -limit, limit).astype(F)
        g = np.minimum(e["g"][lo:hi], limit).astype(F)
        prod.append(V.mul(V.silu(g), u))
    P = c.vm(np.concatenate(prod))
    W = c.vm(np.asarray([e["weight"] for e in ex], F))
    o = c.buf(len(ex) * rows)
    c.op(nout=len(ex), nin=rows, abase=P, aso=rows, asi=1, bbase=W, bso=1, bsi=0, m1=I.M1_AB, rnd=1, obase=o,
         oso=rows, osi=1)
    c.check("route weight x silu(g)*u, BF16 (the w2 input)", o, np.concatenate([e["a"][lo:hi] for e in ex]))
    return [("ffn.route_w", 0, "write")]


def chain_argmax(B, VC, I, c, logits):
    lg = logits[DIE * VOCAB_DIE:(DIE + 1) * VOCAB_DIE]
    la = c.vm(lg)
    o = c.buf(8)
    c.op(nout=1, nin=len(lg), abase=la, aso=len(lg), asi=1, red=I.RED_MAX, redwhole=1, rbase=o, dst=0)
    c.check("die max logit", o, [np.max(lg)])
    return [("head.argmax", 0, "result")]


def build_cases(out: Path):
    import dshbm_baseline_measure as B
    import hdc_golden as G
    import hdc_isa_v41 as I
    import rtl_hdc_v41x_vec_campaign as VC
    cases = []

    def new(name, layer, fn, meta=None):
        c = B.Chain(name, VC)
        c.meta = dict(layer=layer, fn=fn, **(meta or {}))
        return c

    def done(c, nodes):
        c.meta["nodes"] = [dict(node=n, op=k, event=ev) for n, k, ev in nodes]
        cases.append(dict(name=c.name, meta=c.meta, init=c.init, cr_lo=c.cr_lo, cr_hi=c.cr_hi, ops=c.ops,
                          checks=[(lab, ad, G.bits(w).astype(np.uint32), "golden") for lab, ad, w, _k in c.checks]))

    snaps = {}
    for L in LAYERS:
        p = out / f"snap_L{L:02d}.pkl"
        if p.exists():
            snaps[L] = pickle.loads(p.read_bytes())
    for L, s in snaps.items():
        ln = f"L{L}"
        for which, w, hp_i in (("attn", s["attn_norm_w"], 0), ("ffn", s["ffn_norm_w"], 1)):
            c = new(f"{ln}.{which}.hc_mix", ln, "hc_mix")
            c.eps, c.hc_eps = s["eps"], s["hc_eps"]
            nodes = chain_hc_mix(B, VC, I, c, s["hc"][f"hc.{which}"])
            done(c, [(f"{which}.{n}", k, e) for n, k, e in nodes])
            hp = s["hc"]["hc_pre"][hp_i]
            c = new(f"{ln}.{which}.hc_pre_norm", ln, "hc_pre_norm")
            c.eps = s["eps"]
            want = V_rms(hp["out"], w, s["eps"])
            nodes = chain_hc_pre_norm(B, VC, I, c, hp["h"], hp["pre"], w, want)
            done(c, [(f"{which}.{n}", k, e) for n, k, e in nodes])
            c = new(f"{ln}.{which}.hc_post", ln, "hc_post")
            nodes = chain_hc_post(B, VC, I, c, s["hc"]["hc_post"][hp_i])
            done(c, [(f"{which}.{n}", k, e) for n, k, e in nodes])
        c = new(f"{ln}.attn.q_norm", ln, "q_norm")
        c.eps = s["eps"]
        _, nodes = chain_rmsnorm(B, VC, I, c, s["q_norm"], "attn.q_norm")
        done(c, nodes)
        c = new(f"{ln}.attn.kv_norm_rope", ln, "kv_norm_rope")
        c.eps = s["eps"]
        y, nodes = chain_rmsnorm(B, VC, I, c, s["kv_norm"], "attn.kv_norm")
        T_ = c.buf(64)
        lower_rope_rows(c, I, y, 1, 512, s["kv_rope"]["cs"], out=T_)
        c.check("kv RoPE tail (pre FP8 QDQ)", T_, np.asarray(s["kv_rope"]["out"])[-64:])
        done(c, nodes + [("attn.kv_rope_qdq:rope", 3, "write")])
        c = new(f"{ln}.attn.q_rope", ln, "q_rope", dict(heads=HEADS_DIE))
        Q = c.vm(s["q_rope"]["x"])
        T_ = c.buf(HEADS_DIE * 64)
        lower_rope_rows(c, I, Q, HEADS_DIE, 512, s["q_rope"]["cs"], out=T_)
        c.check("q RoPE tails, 16 heads", T_, s["q_rope"]["out"][:, -64:])
        done(c, [("attn.q_rope", 0, "write")])
        if "cmp" in s:
            cm = s["cmp"]
            c = new(f"{ln}.attn.cmp.norm_row", ln, "cmp_norm_row")
            c.eps = s["eps"]
            y, nodes = chain_rmsnorm(B, VC, I, c, cm["norm"], "attn.cmp.norm")
            T_ = c.buf(64)
            lower_rope_rows(c, I, y, 1, 512, cm["row_rope"]["cs"], out=T_)
            c.check("compressed row RoPE tail (pre FP4 QDQ)", T_, np.asarray(cm["row_rope"]["out"])[-64:])
            done(c, nodes + [("attn.cmp.row_qdq:rope", 3, "write")])
            c = new(f"{ln}.attn.cmp.k_norm_rope", ln, "cmp_k_norm_rope")
            c.eps = s["eps"]
            y, nodes = chain_rmsnorm(B, VC, I, c, cm["k_norm"], "attn.cmp.k_norm")
            T_ = c.buf(64)
            lower_rope_rows(c, I, y, 1, 128, cm["k_rope"]["cs"], out=T_)
            c.check("index key RoPE tail (pre FP4 QDQ)", T_, np.asarray(cm["k_rope"]["out"])[-64:])
            done(c, nodes + [("attn.cmp.k_rope_qdq:rope", 3, "write")])
        if "idx_q" in s:
            iq = s["idx_q"]
            nh, hd = np.asarray(iq["x"]).shape
            c = new(f"{ln}.attn.idx.q", ln, "idx_q", dict(heads=nh))
            Q = c.vm(iq["x"])
            T_ = c.buf(nh * 64)
            lower_rope_rows(c, I, Q, nh, hd, iq["cs"], out=T_)
            c.check(f"index q RoPE tails, {nh} heads (pre FP4 QDQ)", T_, np.asarray(iq["out"])[:, -64:])
            done(c, [("attn.idx.q:rope", 0, "write")])
        at = s["hc"]["attend"]
        c = new(f"{ln}.attn.softmax_T{at['T']}", ln, "attend", dict(T=at["T"], heads=HEADS_DIE))
        nodes = chain_attend(B, VC, I, c, at)
        done(c, [(f"attn.{n}", k, e) for n, k, e in nodes])
        c = new(f"{ln}.ffn.router_act", ln, "router_act", dict(rows=384 // TP))
        done(c, chain_router_act(B, VC, I, c, s["router"]))
        c = new(f"{ln}.ffn.route", ln, "route")
        done(c, chain_route(B, VC, I, c, s["router"], s["route_scale"]))
        c = new(f"{ln}.ffn.swiglu", ln, "swiglu", dict(rows=2304 // TP, experts=6))
        done(c, chain_swiglu(B, VC, I, c, s["experts"], s["limit"], routed=True))
        c = new(f"{ln}.ffn.shared_swiglu", ln, "shared_swiglu", dict(rows=2304 // TP))
        done(c, chain_swiglu(B, VC, I, c, s["experts"], s["limit"], routed=False))
        c = new(f"{ln}.ffn.route_w", ln, "route_w", dict(rows=2304 // TP, experts=6))
        done(c, chain_route_w(B, VC, I, c, s["experts"], s["limit"]))
    hp = out / "snap_head.pkl"
    if hp.exists():
        h = pickle.loads(hp.read_bytes())
        c = new("head.hc_pre_norm", "head", "hc_pre_norm")
        c.eps = h["eps"]
        nodes = chain_hc_pre_norm(B, VC, I, c, h["h"], h["pre"], h["w"], h["xf"])
        done(c, [(f"head.{n}", k, e) for n, k, e in nodes])
        c = new("head.argmax", "head", "argmax", dict(logits=VOCAB_DIE))
        done(c, chain_argmax(B, VC, I, c, h["logits"]))
    return cases


def V_rms(x, w, eps):
    import hdc_golden_v41 as V
    return V.rmsnorm_bf16(x, w, eps)


def cmd_prep(a):
    out = Path(a.out)
    cases = build_cases(out)
    if a.fns:
        cases = [c for c in cases if c["meta"]["fn"] in a.fns.split(",")]
    snaps = sorted(out.glob("snap_*.pkl"))
    h = hashlib.sha256()
    for p in snaps:
        h.update(p.read_bytes())
    (out / a.cases).write_bytes(pickle.dumps(dict(cases=cases, snapshots_sha256=h.hexdigest())))
    print("cases", len(cases), [c["name"] for c in cases])
    return 0


def cmd_check(a):
    import dshbm_baseline_measure as B
    return B.cmd_su_check(argparse.Namespace(out=a.out, cases=a.cases))


def cmd_run(a):
    import dshbm_baseline_measure as B
    bc, rt = VARIANTS[a.variant]
    ns = argparse.Namespace(out=a.out, cases=a.cases, bcast=bc, ret=rt, mlat=MLAT, alat=ALAT, n=a.n, m=a.m, fp=a.fp,
                            work=a.work)
    return B.cmd_su_run(ns)


def cmd_equiv(a):
    import dshbm_baseline_measure as B
    out = Path(a.out)
    tag = lambda fp: out / f"su_N64_M16_b0r0m{MLAT}a{ALAT}_{fp}{'' if a.cases == 'su_cases.pkl' else '_' + Path(a.cases).stem}.json"  # noqa: E731
    return B.cmd_su_equiv(argparse.Namespace(su=f"{tag('rtl')},{tag('dpi_beh')}", record=str(out / "su_equiv.json")))


# ======================================================================================================================
# select: ot_hdc_select (K 6, FP32) on the real router scores of each layer
# ======================================================================================================================
def cmd_select(a):
    import rtl_hdc_v41_select_campaign as SC
    import hdc_golden_v41 as V
    out = Path(a.out)
    vl = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
    verilator = str(vl) if vl.exists() else "verilator"
    work = Path(a.work or out / "select_work")
    work.mkdir(parents=True, exist_ok=True)
    rows = []
    exes = {}
    for K, order in ((6, 0), (6, 1)):
        obj = work / f"obj_K{K}_o{order}"
        if not (obj / "Vtb_hdc_select").exists():
            subprocess.run([verilator, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "--top-module", "tb_hdc_select",
                            f"-GK={K}", "-GVW=32", "-GIW=9", f"-GORDER={order}", "-Mdir", str(obj), str(SC.RTL),
                            str(SC.TB), str(SC.HARNESS), "-CFLAGS", "-O1"], check=True, capture_output=True)
        exes[(K, order)] = obj / "Vtb_hdc_select"
    for L in LAYERS:
        p = out / f"snap_L{L:02d}.pkl"
        if not p.exists():
            continue
        rt = pickle.loads(p.read_bytes())["router"]
        v = np.asarray(rt["biased"], F)
        ids = list(range(384))
        golden = sorted(int(i) for i in V.topk_lowest_index(v, 6))
        assert golden == rt["ids"]
        cfgs = {
            # the die's top-6 of 384 on ONE unit, ascending-index order (top6 + top6_order in one pass)
            "one_unit_384_ascending": ((6, 1), [(v, ids, 6)]),
            # the model's select_local: 64 units x 6 elements each, rank order (one unit's 6-element segment)
            "per_unit_6_rank": ((6, 0), [(v[0:6], ids[0:6], 6)]),
            # the model's select_final ascending pass on the 6 selected (id order)
            "order_6_ascending": ((6, 1), [(v[golden], golden, 6)]),
        }
        for name, ((K, order), segs) in cfgs.items():
            fin, fexp, n_el, n_out, h = SC.write_vectors(segs, K, 32, 9, order, work, f"L{L}_{name}")
            r = subprocess.run([str(exes[(K, order)]), f"+IN={fin}", f"+EXP={fexp}", "+BUBBLE=0", "+GAP=0", "+SEED=1"],
                               capture_output=True, text=True).stdout
            rec = SC.parse(r)
            rows.append(dict(layer=f"L{L}", case=name, K=K, order="ascending index" if order else "rank",
                             vectors_sha256=h, **rec))
            print(L, name, rec, flush=True)
    res = dict(schema="opentallas.dsrom.1m_su_select.v1", generated_utc=now(), source_commit=git_head(),
               simulator=subprocess.run([verilator, "--version"], capture_output=True, text=True).stdout.strip(),
               rows=rows, status="pass" if rows and all(r["pass"] for r in rows) else "fail",
               source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (SC.RTL, SC.TB, SC.HARNESS)})
    (out / "select.json").write_text(json.dumps(res, indent=1) + "\n")
    print("SELECT", res["status"])
    return 0 if res["status"] == "pass" else 1


# ======================================================================================================================
# quant: ot_hdc_actquant / ot_hdc_fp4qdq on the golden L20 (and other layers') quantiser inputs
# ======================================================================================================================
QUANT_TB = ROOT / "rtl/test/dsrom_sys/tb_dsrom_1m_quant.sv"
QUANT_RTL = [ROOT / "rtl/hdc/v41/ot_hdc_actquant.sv", ROOT / "rtl/hdc/v41/ot_hdc_fp4qdq.sv"]
AQ_INSTANCES_MODEL = 1024 // 32     # decode_critical_path prices actquant as an SU element-wise op over 1,024 lanes


def quant_sets(s):
    """{node suffix: (kind, part, blocks)}: kind 'fp8' (quant_fp8 codes + exponent + qdq_fp8), 'fp4' (qdq_fp4_e8m0),
    'q4' (qdq_fp4_e4m3, block 16, two blocks a beat)."""
    import hdc_golden_v41 as V
    hp = s["hc"]["hc_pre"]
    rows = 2304 // TP
    lo, hi = DIE * rows, (DIE + 1) * rows
    routed = [e for e in s["experts"] if e["weight"] is not None]
    shared = [e for e in s["experts"] if e["weight"] is None]
    out = {
        "attn.quant": ("fp8", "whole", V.rmsnorm_bf16(hp[0]["out"], s["attn_norm_w"], s["eps"])),
        "attn.q_quant": ("fp8", "whole", s["q_norm"]["out"]),
        "attn.z_quant": ("fp8", "whole", s["hc"]["attend"]["z"][DIE * 2048:(DIE + 1) * 2048]),
        "ffn.quant": ("fp8", "whole", V.rmsnorm_bf16(hp[1]["out"], s["ffn_norm_w"], s["eps"])),
        "ffn.quant2": ("fp8", "whole", np.concatenate([e["a"][lo:hi] for e in routed])),
        "ffn.shared_quant": ("fp8", "whole", np.concatenate([e["a"][lo:hi] for e in shared])),
        "attn.kv_rope_qdq": ("fp8", "qdq", np.asarray(s["kv_rope"]["out"], F)),
    }
    if "cmp" in s:
        out["attn.cmp.k_rope_qdq"] = ("fp4", "qdq", np.asarray(s["cmp"]["k_rope"]["out"], F))
        out["attn.cmp.row_qdq"] = ("q4", "qdq", np.asarray(s["cmp"]["row_rope"]["out"], F))
    if "idx_q" in s:
        out["attn.idx.q"] = ("fp4", "qdq", np.asarray(s["idx_q"]["out"], F).reshape(-1))
    return out


def cmd_quant(a):
    import rtl_hdc_v41_blockdot_campaign as BC
    import hdc_golden_v41 as V
    out = Path(a.out)
    work = Path(a.work or out / "quant_work")
    work.mkdir(parents=True, exist_ok=True)
    vl = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
    verilator = str(vl) if vl.exists() else "verilator"
    obj = work / "obj"
    exe = obj / "Vtb_dsrom_1m_quant"
    if not exe.exists():
        subprocess.run([verilator, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module",
                        "tb_dsrom_1m_quant", "-Mdir", str(obj), *map(str, QUANT_RTL), *map(str, BC.LIB), str(QUANT_TB)],
                       check=True,
                       capture_output=True)
    rows = []
    layers = [int(x) for x in a.layers.split(",")] if a.layers else list(LAYERS)
    for L in layers:
        s = pickle.loads((out / f"snap_L{L:02d}.pkl").read_bytes())
        for node, (kind, part, x) in quant_sets(s).items():
            x = np.asarray(x, F).reshape(-1)
            assert len(x) % 32 == 0
            blocks = x.reshape(-1, 32)
            d = work / f"L{L}_{node}"
            d.mkdir(exist_ok=True)
            if kind == "q4":
                with open(d / "q4_in.mem", "w") as fi, open(d / "q4_exp.mem", "w") as fe:
                    for b in blocks:
                        fi.write(f"{BC.hexw(V.bits(b), 32):0256x}\n")
                        f_, y = BC.q4_expect(b)
                        fe.write(f"{f_:01x}{BC.hexw(y, 16):0128x}\n")
                yq = (np.concatenate([BC.q4_expect(b)[1] for b in blocks]).astype(np.uint32) << 16).view(F)
                golden_ok = same(V.qdq_fp4_e4m3(x, 16), yq)
                args = [f"+NQ4={len(blocks)}"]
            else:
                fp4 = kind == "fp4"
                ys = []
                with open(d / "aq_in.mem", "w") as fi, open(d / "aq_exp.mem", "w") as fe:
                    for b in blocks:
                        fi.write(f"{int(fp4):01x}{BC.hexw(V.bits(b), 32):0256x}\n")
                        f_, e, codes, y = BC.aq_expect(b, fp4)
                        ys.append(np.asarray(y, np.uint32))
                        fe.write(f"{f_:01x}{e & 0xFFF:03x}{BC.hexw(codes, 8):064x}{BC.hexw(y, 16):0128x}\n")
                want = V.qdq_fp4_e8m0(x) if fp4 else V.qdq_fp8(x)
                golden_ok = same(want, (np.concatenate(ys) << 16).view(F))
                args = [f"+NAQ={len(blocks)}"]
            r = subprocess.run([str(exe), *args], cwd=d, capture_output=True, text=True).stdout
            import re
            m = re.search(r"DSQ naq=(\d+) checked=(\d+) errors=(\d+) nq4=(\d+) checked=(\d+) errors=(\d+) "
                          r"first_in=(-?\d+) last_out=(-?\d+)", r)
            naq, ca, ea, nq4, cb, eb, fi_, lo_ = map(int, m.groups())
            beats = len(blocks) if kind != "q4" else len(blocks)      # q4: one 32-element beat = two 16-blocks
            cyc = lo_ - fi_ + 1
            lat = cyc - beats                                         # fixed latency beyond the stream
            inst = AQ_INSTANCES_MODEL
            rows.append(dict(layer=f"L{L}", node=node, part=part, kind=kind, elements=int(len(x)), beats=beats,
                             unit="ot_hdc_fp4qdq" if kind == "q4" else "ot_hdc_actquant",
                             first_in=fi_, last_out=lo_, cycles_one_instance=cyc, latency_after_stream=lat,
                             exact=bool("PASS" in r and ea == 0 and eb == 0 and (ca + cb) == beats and golden_ok),
                             golden_function_check=golden_ok,
                             cycles_model_instances=-(-beats // inst) + lat, model_instances=inst))
            print(rows[-1]["layer"], node, kind, beats, cyc, rows[-1]["exact"], flush=True)
    res = dict(schema="opentallas.dsrom.1m_su_quant.v1", generated_utc=now(), source_commit=git_head(),
               simulator=subprocess.run([verilator, "--version"], capture_output=True, text=True).stdout.strip(),
               rows=rows, status="pass" if rows and all(r["exact"] for r in rows) else "fail",
               source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (*QUANT_RTL, QUANT_TB,
                                                                          ROOT / "tools/rtl_hdc_v41_blockdot_campaign.py")})
    (out / "quant.json").write_text(json.dumps(res, indent=1) + "\n")
    print("QUANT", res["status"])
    return 0 if res["status"] == "pass" else 1


# ======================================================================================================================
# record: node -> measured, against the model
# ======================================================================================================================
def model_nodes():
    """The S81 per-layer graph (tools/dsrom_1m_measure.s58_graph), its SU/SFU nodes' model price and the parts of
    it the model charges for the network (VMC_FUSED fusion classes) and the domain crossing (W18 CDC)."""
    import dsrom_1m_measure as M
    import uarch_model as u
    g, T, p = M.s58_graph()
    fc = u.su_fusion_classes(g)
    out = {}
    for n, nd in g.nodes.items():
        if not (n.startswith(("L0.", "L20.", "L3.", "L24.", "head.", "E1."))):
            continue
        sl = nd["kind"] in u.SLOW_KINDS
        cdc = (u.CDC_W18["fast_to_slow_slow_cycles"] / SLOW_HZ
               if sl and any(g.nodes[x]["kind"] not in u.SLOW_KINDS for x in nd["deps"]) else 0.0)
        net = fc[n]["extra_cycles"](u.VMC_FUSED["fusion"]) / SLOW_HZ if n in fc else 0.0
        out[n] = dict(kind=nd["kind"], resource=nd["resource"], desc=nd["desc"],
                      issue_us=nd["issue"] * 1e6, depth_us=nd["depth"] * 1e6, ctrl_us=nd["ctrl"] * 1e6,
                      model_us=(nd["issue"] + nd["depth"] + nd["ctrl"]) * 1e6,
                      network_us=net * 1e6, cdc_us=cdc * 1e6, fusion_class=fc[n]["cls"] if n in fc else None,
                      network_slow_cycles=fc[n]["extra_cycles"](u.VMC_FUSED["fusion"]) if n in fc else 0.0)
    return out


def _completion(po, ev):
    if ev == "result":
        return po["last_result"]
    return po["last_write"] if po["last_write"] is not None else po["last_result"]


def node_rows(su):
    """Per chain: each node's completion cycle and its increment over the previous node of the chain."""
    rows = {}
    for ch in su["chains"]:
        if ch.get("exact") is None:
            continue
        nodes = ch["nodes"]
        prev = 0
        for nd in nodes:
            comp = _completion(ch["per_op"][nd["op"]], nd["event"])
            rows[(ch["chain"], nd["node"])] = dict(chain=ch["chain"], completion=comp, increment=comp - prev,
                                                   op=nd["op"], event=nd["event"])
            prev = comp
    return rows


def su_ok(ch):
    if ch["exact"] is None:
        return False
    if ch["exact"]:
        return True
    return ch["fn"] == "router_act" and all(x["bit_exact"] for x in ch["checks"]) and \
        ch["unit_reference"].get("faults") == 0 and ch["unit_reference"].get("vm_mismatch_words") == 0


def cmd_record(a):
    import decode_critical_path as DCP
    out = Path(a.out)
    gold = json.loads((out / "golden.json").read_text())
    tagu = f"N{a.n}_M{a.m}_b0r0m{MLAT}a{ALAT}_{a.fp}"
    bw, rw = VARIANTS["wired"]
    tagw = f"N{a.n}_M{a.m}_b{bw}r{rw}m{MLAT}a{ALAT}_{a.fp}"
    sfx = "" if a.cases == "su_cases.pkl" else "_" + Path(a.cases).stem
    su_u = json.loads((out / f"su_{tagu}{sfx}.json").read_text())
    su_w = json.loads((out / f"su_{tagw}{sfx}.json").read_text()) if (out / f"su_{tagw}{sfx}.json").exists() else None
    xs = "_" + Path(a.extra_cases).stem
    extra_runs = {}
    for su_, tg in ((su_u, tagu), (su_w, tagw)):
        f_ = out / f"su_{tg}{xs}.json"
        if su_ is not None and f_.exists():
            x_ = json.loads(f_.read_text())
            have = {c_["chain"] for c_ in su_["chains"]}
            su_["chains"] += [c_ for c_ in x_["chains"] if c_["chain"] not in have]
            extra_runs[tg] = dict(file=f_.name, status=x_["status"], cases_sha256=x_["cases_sha256"])
    eqv = json.loads((out / "su_equiv.json").read_text()) if (out / "su_equiv.json").exists() else None
    sel = json.loads((out / "select.json").read_text()) if (out / "select.json").exists() else None
    model = model_nodes()
    sk = DCP.sinkhorn_unit()
    SK_US = lambda: sk["clocks"] / sk["fmax_hz"] * 1e6            # noqa: E731
    nu = node_rows(su_u)
    nw = node_rows(su_w) if su_w else {}
    exact_u = {ch["chain"]: su_ok(ch) for ch in su_u["chains"]}
    exact_w = {ch["chain"]: su_ok(ch) for ch in su_w["chains"]} if su_w else {}
    chains_u = {ch["chain"]: ch for ch in su_u["chains"]}
    mapping, nodes = [], {}
    graph_layer = {"L20": "L20", "L0": "L0", "L3": "L3", "L24": "L24", "head": "head"}
    for (chain, node), r in sorted(nu.items()):
        L = chains_u[chain]["layer"]
        base, _, part = node.partition(":")
        gname = base if base.startswith("head.") else f"{graph_layer[L]}.{base}"
        mn = model.get(gname)
        cyc = r["increment"]
        us = cyc / SLOW_HZ * 1e6
        wired = nw.get((chain, node))
        row = dict(node=gname, chain=chain, op=r["op"], event=r["event"], part=part or "whole",
                   measured_cycles=cyc, clock_hz=SLOW_HZ, clock_domain="serial-chain 0.9 GHz (AGENTS.md; SU/SFU)",
                   measured_cycles_1p2GHz_equiv=round(cyc * FAST_HZ / SLOW_HZ, 2), us=round(us, 5),
                   exact=exact_u[chain],
                   wired_measured_cycles=wired["increment"] if wired else None,
                   wired_us=round(wired["increment"] / SLOW_HZ * 1e6, 5) if wired else None,
                   wired_exact=exact_w.get(chain) if wired else None)
        if mn:
            comp = us + mn["network_us"] + mn["cdc_us"]     # the bench's own controller issue is inside `us`
            row.update(model_us=round(mn["model_us"], 5), model_issue_us=round(mn["issue_us"], 5),
                       model_depth_us=round(mn["depth_us"], 5), model_ctrl_us=round(mn["ctrl_us"], 5),
                       model_network_us=round(mn["network_us"], 5), model_cdc_us=round(mn["cdc_us"], 5),
                       model_unit_us=round(mn["model_us"] - mn["network_us"] - mn["cdc_us"] - mn["ctrl_us"], 5),
                       composed_us=round(comp, 5) if part == "" else None,
                       fusion_class=mn["fusion_class"], resource=mn["resource"], desc=mn["desc"])
        if mn and part == "front" and gname.endswith("hc.sinkhorn"):
            row["plus_sinkhorn_unit_us"] = round(SK_US(), 5)
            row["composed_us"] = round(us + SK_US() + mn["cdc_us"], 5)
            row["note"] = ("measured SU front (row max + exp over the 4 x 4 comb) + the cited ot_hdc_sinkhorn unit "
                           "(41 unit clocks at its routed fmax); the front's network stages are inside the model's "
                           "sinkhorn node price, so none are added")
        if mn and part == "rope":
            row["note"] = "RoPE part only; the FP8/FP4 QDQ of this node has no SU lowering (stays modelled)"
        mapping.append(row)
        if part in ("", "front", "rope"):
            nodes.setdefault(gname, dict(row, partial=part == "rope"))
    # the router select (ot_hdc_select, 1.2 GHz streaming domain) on the real scores + bias
    if sel:
        for r in sel["rows"]:
            for gname in ((f"{r['layer']}.ffn.top6", f"{r['layer']}.ffn.top6_order")
                          if r["case"] == "one_unit_384_ascending" else
                          (f"{r['layer']}.ffn.top6",) if r["case"] == "per_unit_6_rank" else
                          (f"{r['layer']}.ffn.top6_order",)):
                mn = model.get(gname, {})
                cyc = r["elements"] - 1 + r["latency_max"] + r["outputs"]   # first accept -> last output beat
                mapping.append(dict(node=gname, chain=f"select.{r['case']}", measured_cycles=cyc,
                                    bench_cycles_incl_reset_drain=r["cycles"],
                                    clock_hz=FAST_HZ, clock_domain="streaming 1.2 GHz", us=round(cyc / FAST_HZ * 1e6, 5),
                                    exact=r["pass"], latency_after_last=r["latency_max"], elements=r["elements"],
                                    model_us=round(mn.get("model_us", 0.0), 5),
                                    note={"one_unit_384_ascending": "the die's 384 scores on ONE unit, ascending-index "
                                          "output: covers top6 + top6_order together (bench cycles incl. reset/drain)",
                                          "per_unit_6_rank": "one of the model's 64 select units: a 6-element segment, "
                                          "rank order (the 64-way merge of select_local is unbuilt)",
                                          "order_6_ascending": "the model's select_final ascending-index pass on the "
                                          "6 selected"}[r["case"]]))
    # the attention tile's P.V pass (cited) for the attend nodes
    for L, T in (("L0", 128), ("L3", 640), ("L20", 640), ("L24", 640)):
        pv = dict(T640=(231, 449), T128=(103, 193))[f"T{T}"]
        mn = model.get(f"{L}.attn.pv", {})
        mapping.append(dict(node=f"{L}.attn.pv", chain="cited w11_attn_ploader pwords2_psup2",
                            measured_cycles=pv[1] - pv[0], clock_hz=FAST_HZ, clock_domain="streaming 1.2 GHz",
                            us=round((pv[1] - pv[0]) / FAST_HZ * 1e6, 5), exact=True,
                            model_us=round(mn.get("model_us", 0.0), 5),
                            note="last_score -> last_pv of the measured tile job (P handed over by the bench 9 cycles "
                                 "after the last score at 2 words/cycle); synthetic golden vectors of "
                                 "v41_full_attention_numeric, not this token's"))
    # the chains as wholes: total measured vs the sum of the nodes they replace
    chains = []
    for ch in su_u["chains"]:
        if ch["exact"] is None:
            chains.append(dict(chain=ch["chain"], skipped=ch.get("skipped")))
            continue
        nn = [n["node"] for n in ch["nodes"]]
        L = ch["layer"]
        gn = [(x if x.startswith("head.") else f"{L}.{x}").partition(":")[0] for x in nn]
        last = ch["nodes"][-1]
        tot = _completion(ch["per_op"][last["op"]], last["event"])
        msum = sum(model[g]["model_us"] for g in dict.fromkeys(gn) if g in model)
        chains.append(dict(chain=ch["chain"], layer=L, nodes_replaced=list(dict.fromkeys(gn)),
                           partial_nodes=[x for x in nn if ":" in x], total_cycles=tot,
                           total_us=round(tot / SLOW_HZ * 1e6, 5), model_sum_us=round(msum, 5),
                           wired_total_cycles=(next((c["cycles_end"] for c in su_w["chains"] if c["chain"] == ch["chain"]),
                                                    None) if su_w else None),
                           ops=ch["ops"], exact=exact_u[ch["chain"]], cycles_end=ch["cycles_end"],
                           checks=[dict(label=x["label"], n=x["n"], bit_exact=x["bit_exact"]) for x in ch["checks"]]))
    # cited / separately measured units
    cited = dict(
        sinkhorn_unit=dict(nodes=["*.hc.sinkhorn (after the measured front: row max + exp)"], clocks=sk["clocks"],
                           fmax_hz=sk["fmax_hz"], us=round(sk["clocks"] / sk["fmax_hz"] * 1e6, 5), closed=sk["closed"],
                           sources=sk["sources"], exact="campaign pass on real hc_mixes data (golden-equal)"),
        attention_pv=dict(nodes=["*.attn.pv"], record="results/rtl/w11_attn_ploader.json (pwords2_psup2)",
                          T640=dict(last_score=231, pv_first=240, last_pv=449, pv_pass_cycles=449 - 231),
                          T128=dict(last_score=103, pv_first=112, last_pv=193, pv_pass_cycles=193 - 103),
                          clock_hz=FAST_HZ,
                          note="the tile job measures q.k AND P.V with the probabilities supplied by the bench "
                               "(2 words/cycle) 9 cycles after the last score; the SU softmax between them "
                               "(attn.max/exp/den/sink, measured here) is NOT in the job"),
    )
    if sel:
        cited["router_select"] = dict(record="select.json (this directory, ot_hdc_select K 6 VW 32 on the real "
                                             "scores + bias)", rows=sel["rows"], clock_hz=FAST_HZ)
    unmeasured = [
        dict(nodes=["quantisers: instance count"],
             why="quantisers and QDQ ARE measured (quant.json: ot_hdc_actquant / ot_hdc_fp4qdq, one instance, golden "
                 "blocks bit-exact); the DS-ROM die's actual quantiser instance count is not stated anywhere found: "
                 "decode_critical_path prices actquant as an SU element-wise op over 1,024 lanes (= 32 instances), "
                 "given as us_model_instances; the one-instance figure is `us`."),
        dict(nodes=["attn.hc.fn", "ffn.hc.fn"],
             why="the [24, 20480] FP32 mixes matvec runs on the field/hc engine (resource 'hc'), not the SU; its "
                 "output is a VM operand of the hc_mix chain here."),
        dict(nodes=["attn.scores", "attn.pv"],
             why="attention tile (parent patches attn.scores from the CKV path; attn.pv is cited above from the "
                 "ploader job: last_score -> last_pv)."),
        dict(nodes=["ffn.top6 / ffn.top6_order 64-unit form"],
             why="the model prices 64 ot_hdc_select units x 6 elements + a 64-way merge (select_local); only a "
                 "single unit is measured (select rows); the merge tree is unbuilt."),
        dict(nodes=["E1.hash", "E1.knorm.*", "E1.gather/wkv/deliver"],
             why="Engram (L1/L14): the w17 L01 shard holds only h_in and the Engram output (L1.engram), not the "
                 "hashed table rows, key or value; measuring eng.dot/gate/add needs a replay with the Engram "
                 "tables and tokenizer, not done (skipped as requested)."),
        dict(nodes=["VM-hub network stages per op"],
             why="no separate hub-network RTL bench: given as routed-geometry stages (model VMC_FUSED / "
                 "FUSION_C_ROTATE_PLUS: bcast 6, read 16, write 15, result 6 slow cycles; W11 square_hub on W18b "
                 "plus hub), added in composed_us by the model's fusion class; the 'wired' run puts bcast+read 22 "
                 "/ write 15 on every op as RTL register stages (unfused upper bound)."),
        dict(nodes=["CDC fast->slow"], why="W18 ratio-FIFO latency (4 slow cycles) per crossing edge: modelled, "
                                           "added in composed_us when the model charges it."),
    ]
    totals = {}
    for g_, r in nodes.items():
        L = g_.split(".")[0]
        t = totals.setdefault(L, dict(nodes=0, measured_us=0.0, composed_us=0.0, model_us=0.0, wired_us=0.0,
                                      partial_nodes=[]))
        if r.get("partial"):
            t["partial_nodes"].append(g_)
            continue
        if "us" not in r:
            continue
        t["nodes"] += 1
        t["measured_us"] += r["us"]
        t["composed_us"] += r.get("composed_us") or 0.0
        t["model_us"] += r.get("model_us", 0.0)
        t["wired_us"] += r.get("wired_us") or 0.0
    for t in totals.values():
        for k in ("measured_us", "composed_us", "model_us", "wired_us"):
            t[k] = round(t[k], 4)
    # node_us (parent's composition interface): per layer, graph node suffix -> latency; a chain's total sits on
    # its LAST node, the chain's other nodes carry 0 with covered_by
    node_us_by_layer = {}
    for c in chains:
        if c.get("skipped"):
            continue
        L = c["layer"]
        ch = chains_u[c["chain"]]
        names = [n["node"] for n in ch["nodes"]]
        tot_us = c["total_us"]
        extra = 0.0
        for k, n in enumerate(names):
            base, _, part = n.partition(":")
            suf = base[len("head."):] if base.startswith("head.") else base
            g_ = base if base.startswith("head.") else f"{L}.{base}"
            mn = model.get(g_, {})
            last = k == len(names) - 1
            if part == "front":                                   # Sinkhorn: + the cited unit
                extra = SK_US()
            e = dict(us=round(tot_us + (extra if last else 0.0), 5) if last else 0.0,
                     chain=c["chain"], exact=c["exact"], model_us=round(mn.get("model_us", 0.0), 5))
            if not last:
                e["covered_by"] = c["chain"]
            else:
                e["chain_nodes"] = [x.partition(":")[0] for x in names]
                wsum = [nw.get((c["chain"], x)) for x in names]
                e["wired_us"] = (round(sum(w_["increment"] for w_ in wsum) / SLOW_HZ * 1e6 + (extra if last else 0.0), 5)
                                 if all(wsum) else None)
                e["chain_model_us"] = c["model_sum_us"]
                e["composed_us"] = round(e["us"] + sum(model.get(
                    (x.partition(":")[0] if x.startswith("head.") else f"{L}." + x.partition(":")[0]), {}).get(
                    "network_us", 0.0) for x in names if not x.endswith(":front")), 5)
            if part == "rope":
                e["partial"] = "RoPE only; FP8/FP4 QDQ unmeasured (modelled)"
            if part == "front":
                e["includes"] = f"SU front (row max + exp) + ot_hdc_sinkhorn {sk['clocks']} clocks at {sk['fmax_hz']/1e6:.1f} MHz"
            node_us_by_layer.setdefault("head" if L == "head" else L, {})[suf] = e
    for r in mapping:                                              # select and P.V (1.2 GHz units)
        if r["chain"] == "select.one_unit_384_ascending":
            L, suf = r["node"].split(".", 1)
            node_us_by_layer[L][suf] = dict(us=0.0 if suf == "ffn.top6" else r["us"], chain=r["chain"],
                                            exact=r["exact"], model_us=r["model_us"],
                                            **({"covered_by": r["chain"]} if suf == "ffn.top6" else
                                               {"chain_nodes": ["ffn.top6", "ffn.top6_order"],
                                                "note": "one ot_hdc_select unit, 384 elements, ascending output"}))
        if r["chain"].startswith("cited w11_attn_ploader"):
            L, suf = r["node"].split(".", 1)
            node_us_by_layer[L][suf] = dict(us=r["us"], chain=r["chain"], exact=True, model_us=r["model_us"],
                                            note="cited tile P.V pass (last score -> last P.V), synthetic vectors")
    # the quantisers (ot_hdc_actquant / ot_hdc_fp4qdq, one instance, golden blocks back to back)
    qj = json.loads((out / "quant.json").read_text()) if (out / "quant.json").exists() else None
    bw_, rw_ = VARIANTS["wired"]
    for r in (qj["rows"] if qj else []):
        g_ = f"{r['layer']}.{r['node']}"
        mn = model.get(g_, {})
        cyc = r["cycles_one_instance"]
        e = dict(us=round(cyc / SLOW_HZ * 1e6, 5), cycles=cyc, clock_hz=SLOW_HZ, chain=f"quant.{r['unit']}",
                 exact=r["exact"], part=r["part"], blocks=r["beats"], latency_after_stream=r["latency_after_stream"],
                 instances=1,
                 us_model_instances=round(r["cycles_model_instances"] / SLOW_HZ * 1e6, 5),
                 model_instances=r["model_instances"],
                 wired_us=round((cyc + bw_ + rw_) / SLOW_HZ * 1e6, 5),
                 wired_us_model_instances=round((r["cycles_model_instances"] + bw_ + rw_) / SLOW_HZ * 1e6, 5),
                 model_us=round(mn.get("model_us", 0.0), 5))
        mapping.append(dict(node=g_, chain=e["chain"], part=r["part"], measured_cycles=cyc, clock_hz=SLOW_HZ,
                            us=e["us"], exact=r["exact"], model_us=e["model_us"], unit=r["unit"], blocks=r["beats"],
                            note="one instance, first block in -> last block out; model_instances = the model's "
                                 "lane-parallel pricing (1,024 SU lanes / 32 = 32 instances), composed from II 1 + "
                                 "fixed latency; wired = + bcast/read 22 + write 15 slow cycles (arithmetic, as the "
                                 "wired SU variant)"))
        L = r["layer"]
        if r["part"] == "whole":
            node_us_by_layer.setdefault(L, {})[r["node"]] = e
            nodes.setdefault(g_, dict(e, node=g_, measured_cycles=cyc))
        else:
            node_us_by_layer.setdefault(L, {}).setdefault(r["node"], dict(us=0.0, chain=None, exact=True))["qdq"] = e
    node_us = dict(node_us_by_layer.get("L20", {}))               # flat: the CSA reference layer (T 640)
    for suf, e in node_us_by_layer.get("L0", {}).items():         # sliding-window layers' T 128 attention
        if suf.startswith("attn.") and suf.split(".")[1] in ("max", "exp", "den", "sink", "normalize", "pv"):
            node_us[f"{suf}@T128"] = e
    for suf, e in node_us_by_layer.get("head", {}).items():
        node_us[f"head.{suf}"] = e
    status = "pass" if all(exact_u.values()) and gold["status"] == "pass" else "fail"
    srcs = ["tools/dsrom_1m_su.py", "tools/dshbm_baseline_measure.py", "tools/rtl_hdc_v41x_vec_campaign.py",
            "tools/hdc_golden_v41.py", "tools/hdc_golden.py", "tools/rtl_v41_fullshape_layer_campaign.py",
            "tools/dsrom_1m_measure.py", "tools/uarch_model.py", "tools/rtl_hdc_v41_select_campaign.py"]
    rec = dict(
        schema="opentallas.dsrom.1m_allmeasured.su.v1", generated_utc=now(), source_commit=git_head(), status=status,
        scope=("DS-ROM S81 per-layer SU/SFU nodes at the 1M token (position 1,048,575), die 0 of a TP4 group, "
               "measured in RTL on real golden operands; per-node cycles are the increment of the node's last op "
               "completion over the previous node of its chain (chains run back to back with the unit's own "
               "chaining); the parent composes the token."),
        geometry=dict(su_lanes=a.n, sfu_lanes=a.m, MLAT=MLAT, ALAT=ALAT, clock_hz=SLOW_HZ,
                      source="tools/uarch_model.py PRESETS['proposal'] (spec_striped su_lanes 1024 / sfu_lanes 256); "
                             "W11_SERIAL_MEASURED mlat 5 / alat 4 at 1.111 ns SS (0.9 GHz slow domain)",
                      network_model="VMC_FUSED = VMC_PLUS + FUSION_C_ROTATE_PLUS (conservative fusion)",
                      variants={k: dict(BCAST_STAGES=v[0], RET_STAGES=v[1]) for k, v in VARIANTS.items()}),
        shapes=dict(hidden=D, hc=HC, heads_per_die=HEADS_DIE, q_lora=1280, kv=512, T={"L0": 128, "L3/L20/L24": 640},
                    router_rows_per_die=384 // TP, experts=6, expert_rows_per_die=2304 // TP,
                    shared_rows_per_die=2304 // TP, vocab_per_die=VOCAB_DIE),
        simulator=dict(rtl="Verilator 5.050 (~/.local/opentallas-tools/verilator-5.050)", fp=a.fp,
                       fp_note=su_u["config"]["fp_note"],
                       equivalence=None if eqv is None else dict(status=eqv["status"], config="N64/M16 rtl vs dpi_beh",
                                                                 chains=len(eqv["chains"]),
                                                                 identical=sum(r["identical"] for r in eqv["chains"]))),
        golden=dict(status=gold["status"], context=gold["context"], seed=gold["seed"], arith=gold["arith"],
                    layers=gold["layers"], golden_sha256=gold["golden_sha256"], gold_dir=gold["gold_dir"]),
        totals_note=("per layer: sums over the measured whole nodes (serial sums, NOT critical-path time: the "
                     "graph runs some in parallel); composed = measured + the model's routed network stages + CDC"),
        node_us_note=("flat map = layer 20 (CSA, T 640) suffixes, '@T128' = layer 0 sliding attention, 'head.*'; "
                      "node_us_by_layer has L0/L3/L20/L24/head. us = RTL latency at 0.9 GHz (SU) or 1.2 GHz "
                      "(select, P.V) from the chain's first input to the node's result; a chain's total is on its "
                      "LAST node, the others 0 with covered_by; composed_us adds the model's routed network stages "
                      "(VMC_FUSED) of the chain's nodes; CDC and quantisers stay modelled"),
        node_us=node_us, node_us_by_layer=node_us_by_layer,
        totals=totals, nodes=nodes, mapping=mapping, chains=chains, cited=cited, unmeasured=unmeasured,
        runs=dict(unit=dict(file=f"su_{tagu}{sfx}.json", status=su_u["status"], config=su_u["config"],
                            cases_sha256=su_u["cases_sha256"]),
                  wired=None if su_w is None else dict(file=f"su_{tagw}{sfx}.json", status=su_w["status"],
                                                       config=su_w["config"]),
                  extra_case_runs=extra_runs),
        source_sha256={p: sha(ROOT / p) for p in srcs},
        rtl_sha256=su_u["source_sha256"])
    Path(a.record).parent.mkdir(parents=True, exist_ok=True)
    Path(a.record).write_text(json.dumps(rec, indent=1, default=float) + "\n")
    print("RECORD", status, a.record)
    return 0 if status == "pass" else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("golden", "prep", "check", "select", "quant", "run", "equiv", "record"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--layers", default=None)
    ap.add_argument("--fns", default=None, help="prep: only these chain fns (comma list)")
    ap.add_argument("--extra-cases", default="su_cases_rw.pkl", help="record: merged extra case set if run")
    ap.add_argument("--cases", default="su_cases.pkl")
    ap.add_argument("--variant", choices=tuple(VARIANTS), default="unit")
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--m", type=int, default=256)
    ap.add_argument("--fp", choices=("rtl", "dpi", "dpi_beh"), default="dpi_beh")
    ap.add_argument("--work", default=None)
    ap.add_argument("--record", default=str(ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/su.json"))
    a = ap.parse_args()
    return dict(golden=cmd_golden, prep=cmd_prep, check=cmd_check, select=cmd_select, quant=cmd_quant, run=cmd_run,
                equiv=cmd_equiv,
                record=cmd_record)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
