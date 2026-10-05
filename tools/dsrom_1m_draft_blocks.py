#!/usr/bin/env python3
"""DS-ROM (DeepSeek-V4.1-Flash, S81, TP4 a stage) at the 1M token: the three DSpark draft blocks (mtp.0 .. mtp.2,
gamma 5 = 5 block rows) MEASURED element by element at FULL SHAPE on the full-shape RTL units the 1M AR composition
uses, on the released mtp.* weights and the golden draft's own activations, then composed on the block's fixed
dependency graph (replaces the reduced-vehicle block5 x transfer ratio of results/rtl/dsrom_dspark_step_slices_20261004).

WHAT A BLOCK IS (tools/hdc_golden_v41.py Model.dspark_stage; tools/hdc_program_v41.py draft_body / attention(draft)):
a V4.1 layer over the 5 block rows: hc mixes, hc_pre + RMSNorm, wq_a | wkv, q_norm, wq_b, q RoPE, kv_norm + RoPE +
FP8 QDQ (every row's KV goes to the stage's window cache first), then -- ONE ROW AT A TIME (the program's serial
section) -- q.k over the 128 window rows + the 5 block rows (T = 133), softmax with the sink, P.V, normalise, inverse
RoPE; then wo_a, wo_b, the TP4 all-reduce, hc_post; hc mixes, hc_pre + RMSNorm, the 128-expert router (sqrt-softplus,
bias, top-3), the shared expert and three routed experts per row, the combine all-reduce, hc_post.

PLACEMENT BASIS.  The S81 canonical binding (results/uarch/dsrom_s81_released_binding_20261004/canonical) leaves the
mtp.* tensors UNOWNED (auxiliary_obligations.json: "MTP ... source owners require additional priced mapping"; the 8
head dies hold embed + head + norm only).  The unified model puts the DSpark stages in the head group (uarch_model
cons_head_dies: embed + head + mtp bytes).  This tool takes the minimum honest placement: each DSpark stage on its own
TP4 group of S81 layer-class dies (2,417 element pairs a die, 128 return regions), its matrices on the S81 allocator's
placement of the backbone SLIDING layer L0 (same shapes: wq_a, wkv, wq_b, wo_a, wo_b, shared expert; routed expert e
on L0 expert e's pairs; the 128-row gate on the first 32 rank rows of L0's gate placement), rank 0 measured.  One
stage hop enters each DSpark stage (head group -> mtp.0 -> mtp.1 -> mtp.2 -> head group).

ROM FIELD AND FIVE VECTORS.  The as-built W17 spine (rtl/v41die/ot_v41_spine_w17w10.sv) runs one PHASE at a time but a
phase carries 1..6 POSITIONS (i_np = positions - 1; one cfg ROM entry, the x of every position streamed in turn,
rows of position p written at obase + p*ops).  The ISA batches a weight op over the slots (hdc_program_v41 mx_m) except
the indirect (routed-expert) ops.  So: wq_a|wkv, wq_b, wo_a, wo_b, gate, shared w1|w3, shared w2 = ONE phase of 5
positions (np = 4); each row's three routed experts = their own one-position phases (15 gu + 15 w2 phases).  Both
the batched and the one-sweep-per-vector timings are measured (np 4 vs 5 x np 0) and reported.

ELEMENTS (each RTL-measured on this token's golden operands, exact vs the golden):
  field     tools/dsrom_1m_field.py vehicle (pinned ot_v41_fieldtop_w17w10, one region at full shape, every region of
            rank 0), multi-position ops, + S81 floorplan wire stages per phase (as field.json total_us_s81_floorplan_wire)
  su        ot_hdc_v41x_vec N1024/M256, MLAT 5/ALAT 4, wired BCAST 22 / RET 15 (tools/dsrom_1m_su.py chains, 5 rows
            op-major: op j of every row before op j+1, as merge_slots issues them), 0.9 GHz
  quant     ot_hdc_actquant one instance on the 5 rows' blocks (dsrom_1m_su quant method)
  select    ot_hdc_select K 3 on the 128 biased scores, one row after another
  sinkhorn  ot_hdc_sinkhorn 41 unit clocks at the routed 151.9 MHz (cited, as the AR composition) a row
  attn      full-geometry attention engine (H16/D512/TD32/NL4, PWORDS 2, psup 2) 5 jobs back to back at T = 133 on
            the golden q, the window + block KV rows and the golden probabilities of die 0
  links     stage hop (ot_dsrom_link_rt + light-FEC budget) at 5 x 40,976 B; TP4 collectives (tb_w15b_v41_tp4) at the
            5-row payloads
Steps (golden + RTL on a compute host; record locally):
    python3 tools/dsrom_1m_draft_blocks.py golden  --out DIR --snapshot SNAP --ref REF
    python3 tools/dsrom_1m_draft_blocks.py fplan|fextract|fbuild|frun --work DIR/field --golden DIR [--snapshot SNAP]
    python3 tools/dsrom_1m_draft_blocks.py suprep --out DIR ; surun --out DIR --variant wired
    python3 tools/dsrom_1m_draft_blocks.py quant|select|attn|links --out DIR
    python3 tools/dsrom_1m_draft_blocks.py record  --out DIR --record results/rtl/dsrom_1m_allmeasured_20261004/draft_blocks.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pickle
import re
import shutil
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
ANCHOR = CTX - 1                  # the 1M reference token's position; the draft block sits at anchor+1 .. anchor+5
SEED = 20260930
ROWS = 5                          # dspark_block_size (gamma 5)
STAGES = 3                        # mtp.0 .. mtp.2
TP, DIE = 4, 0
HEADS_DIE = 16
CLK, SLOW = 1.2e9, 0.9e9
REC = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/draft_blocks.json"
AR_DIR = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004"
REF_DEFAULT = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
SNAP_DEFAULT = Path.home() / (".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/"
                              "dba1be0a40aa45a94ad051997016db3960a90277")
BLOCK5_REDUCED_US = 14.405


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def bits(x):
    return np.asarray(x, dtype=F).view(np.uint32)


def same(a, b):
    return bool(np.array_equal(bits(a).reshape(-1), bits(b).reshape(-1)))


# ======================================================================================================================
# golden: the draft's three stages at the 1M anchor, every operand captured per (stage, row)
# ======================================================================================================================
class WindowCache:
    """state["dsk"][st] for the golden's dspark_window: positions 0 .. anchor exist (len = anchor + 1); only the 128
    window positions anchor-127 .. anchor are ever read.  The anchor's row is REAL (dspark_seed of the 1M token's main
    hidden state: the inputs of layers 37, 38, 39 in the w17 golden shards); the 127 older rows are synthetic and
    format-consistent (the w17 convention: unit-RMS normal x the stage's kv_norm gain, RoPE at the row's position,
    FP8 QDQ), one generator per stage: default_rng([seed, ctx, 4, stage])."""

    def __init__(self, rows: dict, anchor: int):
        self.rows, self.anchor = rows, anchor

    def __len__(self):
        return self.anchor + 1

    def __getitem__(self, p):
        return self.rows[p]


def build_state(m, V, LC, ref: Path):
    zs = [np.load(ref / f"ctx{CTX}_L{L:02d}.npz") for L in m.dspark_targets]
    mh = np.concatenate([m.main_hidden_part(z["h_in"]) for z in zs])
    main_x = V.rmsnorm_bf16(V.linear_q(m.w["mtp.0.main_proj.weight"], mh), m.w["mtp.0.main_norm.weight"], m.eps)
    dsk, desc = [], dict(anchor_row="real: dspark_seed(main_hidden_part(h_in of L37, L38, L39)) at position "
                                    f"{ANCHOR}", older_rows="synthetic: default_rng([seed, ctx, 4, stage]) unit-RMS "
                                                            "normal x kv_norm gain, RoPE at its position, FP8 QDQ",
                         sha256={})
    for st in range(m.n_mtp):
        L = m.L + st
        rows = {ANCHOR: m.dspark_row(L, main_x, ANCHOR)}
        g = np.asarray(m.lw(L, "attn.kv_norm.weight"), F)
        rng = np.random.default_rng([SEED, CTX, 4, st])
        for p in range(ANCHOR - m.window + 1, ANCHOR):
            x = V.to_bf16(rng.standard_normal(m.hd).astype(F) * g)
            rows[p] = V.qdq_fp8(V.rope_tail(x, V.rope_cs(m.freqs_plain, p)))
        dsk.append(WindowCache(rows, ANCHOR))
        desc["sha256"][f"stage{st}"] = hashlib.sha256(b"".join(np.asarray(rows[p], F).tobytes()
                                                               for p in sorted(rows))).hexdigest()
    return {"dsk": dsk}, desc, mh, main_x


def capture_stage(m, V, L, hs, pres, anchor, state):
    """m.dspark_stage(L, ...) with every operand captured per row: the golden's module functions logged and the
    hyper-connection mixes / attention core / expert steps replicated verbatim (as tools/dsrom_1m_su.py _replay does
    for a backbone layer; the stage output is checked bit-exact against the uninstrumented golden)."""
    names = ["linear_q", "rmsnorm_bf16", "rope_tail", "mv", "qdq_fp8"]
    orig = {n: getattr(V, n) for n in names}
    log = []

    def wrap(n):
        f = orig[n]

        def g(*args, **kw):
            r = f(*args, **kw)
            log.append(dict(fn=n, args=args, kw=dict(kw), out=r))
            return r
        return g

    cap = {"hc.attn": [], "hc.ffn": [], "attend": [], "experts": [], "hc_pre": [], "hc_post": []}

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
        cap[f"hc.{which}"].append(dict(x=x.copy(), ss=F(ss), r=F(r), raw=raw.copy(), scale=np.asarray(scale, F).copy(),
                                       base=np.asarray(base, F).copy(), pre=pre, post=post, comb0=comb0,
                                       max=mx.reshape(-1), e=e, comb=comb))
        return pre, post, comb

    def attend(L_, q, kvm, cs, blocks=None):
        assert blocks is None
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
        cap["attend"].append(dict(q=q[:H].copy(), kvm=np.asarray(kvm, F).copy(), T=int(len(kvm)), s_raw=s_raw[:H].copy(),
                                  s=s[:H].copy(), max=mb[:H].copy(), e=e[:H].copy(), es=es[:H].copy(),
                                  sink=np.asarray(sink, F)[:H].copy(), den=den[:H].copy(), pv=pv[:H].copy(),
                                  o0=o0[:H].copy(), o=o[:H].copy(), o_full=o.copy(), cs=cs,
                                  attn_scale=F(m.attn_scale), z=z.copy()))
        return V.linear_q(m.lw(L_, "attn.wo_b.weight"), z)

    def expert(prefix, x, weight=None):
        g0 = V.linear_q(m.w[prefix + "w1.weight"], x)
        u0 = V.linear_q(m.w[prefix + "w3.weight"], x)
        u = np.clip(u0, -m.limit, m.limit).astype(F)
        g = np.minimum(g0, m.limit).astype(F)
        a = V.mul(V.silu(g), u)
        if weight is not None:
            a = V.mul(weight, a)
        cap["experts"].append(dict(prefix=prefix, x=np.asarray(x, F).copy(), g=g0.copy(), u=u0.copy(),
                                   weight=None if weight is None else F(weight), a=V.to_bf16(a)))
        return V.linear_q(m.w[prefix + "w2.weight"], V.to_bf16(a))

    hcp_orig, hcpost_orig = m.hc_pre, m.hc_post

    def hc_pre(x, pre):
        out = hcp_orig(x, pre)
        cap["hc_pre"].append(dict(h=x.copy(), pre=np.asarray(pre, F).copy(), out=out.copy()))
        return out

    def hc_post(y, res, post, comb):
        out = hcpost_orig(y, res, post, comb)
        cap["hc_post"].append(dict(y=np.asarray(y, F).copy(), res=res.copy(), post=post.copy(), comb=comb.copy(),
                                   out=out.copy()))
        return out

    for n in names:
        setattr(V, n, wrap(n))
    m.hc_mixes, m.attend, m.expert, m.hc_pre, m.hc_post = hc_mixes, attend, expert, hc_pre, hc_post
    try:
        out_h, out_pre = m.dspark_stage(L, hs, pres, anchor, state)
    finally:
        for n in names:
            setattr(V, n, orig[n])
        for k in ("hc_mixes", "attend", "expert", "hc_pre", "hc_post"):
            delattr(m, k)
    return out_h, out_pre, cap, log


def row_snaps(m, V, L, cap, log):
    """Split one stage's capture into per-row snapshots in tools/dsrom_1m_su.py's snap format (+ the field x)."""
    R = ROWS
    lw = lambda n: m.lw(L, n)                                                                   # noqa: E731
    by = lambda fn, w: [e for e in log if e["fn"] == fn and e["args"][1] is w]                  # noqa: E731
    qnorm, kvnorm = by("rmsnorm_bf16", lw("attn.q_norm.weight")), by("rmsnorm_bf16", lw("attn.kv_norm.weight"))
    anorm, fnorm = by("rmsnorm_bf16", lw("attn_norm.weight")), by("rmsnorm_bf16", lw("ffn_norm.weight"))
    lin = lambda name: [e for e in log if e["fn"] == "linear_q" and e["args"][0] is m.w[m.P(L) + name]]  # noqa: E731
    wqa, wkv, wqb, wob = lin("attn.wq_a.weight"), lin("attn.wkv.weight"), lin("attn.wq_b.weight"), lin("attn.wo_b.weight")
    gate = [e for e in log if e["fn"] == "mv" and e["args"][0] is lw("ffn.gate.weight")]
    ropes = [e for e in log if e["fn"] == "rope_tail" and not e["kw"].get("inverse", False)]
    q_rope = [e for e in ropes if np.asarray(e["args"][0]).shape == (m.heads, m.hd)]
    kv_rope = [e for e in ropes if np.asarray(e["args"][0]).shape == (m.hd,)]
    for lst, nm in ((qnorm, "q_norm"), (kvnorm, "kv_norm"), (anorm, "attn_norm"), (fnorm, "ffn_norm"), (wqa, "wq_a"),
                    (wkv, "wkv"), (wqb, "wq_b"), (wob, "wo_b"), (gate, "gate"), (q_rope, "q_rope"),
                    (kv_rope, "kv_rope"), (cap["attend"], "attend"), (cap["hc.attn"], "hc.attn"),
                    (cap["hc.ffn"], "hc.ffn")):
        assert len(lst) == R, (nm, len(lst))
    assert len(cap["hc_pre"]) == 2 * R and len(cap["hc_post"]) == 2 * R
    k_exp = m.dspark_k_exp
    assert len(cap["experts"]) == R * (k_exp + 1)
    bias = np.asarray(lw("ffn.gate.bias"), F)
    snaps = []
    for i in range(R):
        raw = gate[i]["out"]
        scores = V.sqrt(V.softplus(raw))
        biased = V.add(scores, bias)
        ids = sorted(int(x) for x in V.topk_lowest_index(biased, k_exp))
        tot = V.seqsum([scores[j] for j in ids])
        den = V.add(tot, F(1e-20))
        wts = np.asarray([V.mul(V.div(scores[j], den), m.route_scale) for j in ids], F)
        ex = cap["experts"][i * (k_exp + 1):(i + 1) * (k_exp + 1)]
        got_ids = [int(e["prefix"].split(".")[-2]) for e in ex if e["weight"] is not None]
        assert got_ids == ids, (i, got_ids, ids)
        assert all(same(e["weight"], w) for e, w in zip([e for e in ex if e["weight"] is not None], wts))
        at = cap["attend"][i]
        snaps.append(dict(
            stage=L - m.L, row=i, layer=L, T=at["T"], eps=F(m.eps), hc_eps=F(m.hc_eps), route_scale=F(m.route_scale),
            limit=F(m.limit), attn_norm_w=np.asarray(lw("attn_norm.weight"), F), ffn_norm_w=np.asarray(lw("ffn_norm.weight"), F),
            hc={"hc.attn": cap["hc.attn"][i], "hc.ffn": cap["hc.ffn"][i], "attend": at,
                "hc_pre": [cap["hc_pre"][i], cap["hc_pre"][R + i]], "hc_post": [cap["hc_post"][i], cap["hc_post"][R + i]]},
            q_norm=dict(x=qnorm[i]["args"][0], w=np.asarray(lw("attn.q_norm.weight"), F), out=qnorm[i]["out"]),
            kv_norm=dict(x=kvnorm[i]["args"][0], w=np.asarray(lw("attn.kv_norm.weight"), F), out=kvnorm[i]["out"]),
            q_rope=dict(x=np.asarray(q_rope[i]["args"][0])[:HEADS_DIE].copy(), cs=q_rope[i]["args"][1],
                        out=np.asarray(q_rope[i]["out"])[:HEADS_DIE].copy()),
            kv_rope=dict(x=kv_rope[i]["args"][0], cs=kv_rope[i]["args"][1], out=kv_rope[i]["out"]),
            router=dict(raw=raw, scores=scores, bias=bias, biased=biased, ids=ids, weights=wts),
            experts=ex,
            # the field's x (and the golden linear outputs for the cross-check)
            fx=dict(attn_norm=anorm[i]["out"], qr=qnorm[i]["out"], o=at["o_full"], z=at["z"], ffn_norm=fnorm[i]["out"]),
            fy=dict(wq_a=wqa[i]["out"], wkv=wkv[i]["out"], wq_b=wqb[i]["out"], gate=raw)))
    return snaps


def cmd_golden(a):
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    V.set_arith("chunk8")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ck = LC.Checkpoint(a.snapshot)
    m, init_sha = LC.build_model(ck, engram=False)
    ref = Path(a.ref)
    reftok = json.loads((ROOT / "results/rtl/w17_v41_1m_reference_token.json").read_text())
    y = int(reftok["next_token"])
    state, sdesc, mh, main_x = build_state(m, V, LC, ref)
    ids = [y] + [m.noise_id] * (m.dspark_block - 1)
    emb = ck.rows("embed.weight", sorted(set(ids)))
    erow = dict(zip(sorted(set(ids)), emb))
    hs = [np.repeat(np.asarray(erow[t], F)[None, :], m.hc, axis=0).astype(F) for t in ids]
    pres = [np.array([1, 0, 0, 0], dtype=F)[:m.hc] for _ in ids]
    summary = dict(y=y, noise_id=m.noise_id, anchor=ANCHOR, positions=[ANCHOR + 1 + i for i in range(ROWS)],
                   state=sdesc, stages={})
    for st in range(m.n_mtp):
        L = m.L + st
        ts = time.time()
        ref_h, ref_pre = m.dspark_stage(L, [h.copy() for h in hs], [p.copy() for p in pres], ANCHOR, state)
        oh, op, cap, log = capture_stage(m, V, L, hs, pres, ANCHOR, state)
        ok = all(same(x, y_) for x, y_ in zip(oh, ref_h)) and all(same(x, y_) for x, y_ in zip(op, ref_pre))
        snaps = row_snaps(m, V, L, cap, log)
        for s in snaps:
            (out / f"snap_S{st}_r{s['row']}.pkl").write_bytes(pickle.dumps(s))
        summary["stages"][f"mtp.{st}"] = dict(
            capture_equals_golden_stage=ok, experts=[s["router"]["ids"] for s in snaps], T=snaps[0]["T"],
            out_sha256=hashlib.sha256(b"".join(np.asarray(h, F).tobytes() for h in oh)).hexdigest(),
            wall_s=round(time.time() - ts, 1))
        print(f"mtp.{st} capture==golden {ok} experts {[s['router']['ids'] for s in snaps]} "
              f"{time.time() - ts:.0f} s", flush=True)
        hs, pres = oh, op
        for k in [k for k in list(m.w) if k.startswith(f"mtp.{st}.")]:
            if not k.startswith("mtp.0.main"):
                del m.w[k]
    summary.update(schema="opentallas.dsrom-1m.draft-blocks.golden.v1", generated_utc=now(), source_commit=git_head(),
                   arith=V.ARITH, golden_sha256={p: sha(ROOT / p) for p in ("tools/hdc_golden_v41.py",
                                                                            "tools/hdc_golden.py")},
                   golden_init_sha256=init_sha, checkpoint=str(a.snapshot), wall_s=round(time.time() - t0, 1),
                   ref_sha256={f"L{L}": sha(ref / f"ctx{CTX}_L{L:02d}.npz") for L in m.dspark_targets},
                   status="pass" if all(v["capture_equals_golden_stage"] for v in summary["stages"].values()) else "fail")
    (out / "golden.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print("GOLDEN", summary["status"], f"{time.time() - t0:.0f} s")
    return 0 if summary["status"] == "pass" else 1


def load_snaps(d: Path):
    return {(st, r): pickle.loads((d / f"snap_S{st}_r{r}.pkl").read_bytes())
            for st in range(STAGES) for r in range(ROWS)}


# ======================================================================================================================
# field: the ROM matvecs on the pinned W17/W10 field vehicle (tools/dsrom_1m_field.py), multi-position phases
# ======================================================================================================================
FIELD_BATCHED = ("a_proj.fp8", "wq_b", "wo_b", "router", "shared_gu", "shared.w2")       # + wo_a.g*
GATE_ROWS_RANK = 128 // TP


def _mtp_entry(e, st):
    """An S81 L0 map entry re-targeted to DSpark stage st (same shape and placement); the 128-row gate keeps the
    first 32 rank rows (superrows 0..15) of L0's 96-row rank-0 gate placement."""
    e = json.loads(json.dumps(e))
    e["tensor"] = e["tensor"].replace("layers.0.", f"mtp.{st}.")
    e["layer"] = 40 + st
    if e["alias"] == "gate":
        keep = GATE_ROWS_RANK // 2
        plans = []
        for seg, pair, s0, cnt, stride, base, words in e["plans"]:
            for k in range(cnt):
                if s0 + k * stride < keep:
                    plans.append([seg, pair, s0 + k * stride, 1, stride, base, words])
        e["plans"] = plans
        e["rows"] = GATE_ROWS_RANK
        e["rank_slices"] = [dict(cols=[0, 5120], rows=[r * GATE_ROWS_RANK, (r + 1) * GATE_ROWS_RANK]) for r in range(TP)]
    return e


def field_x(s, grp, mats):
    """The phase's x for one row (snapshot s), sliced to the rank's K columns, as FP32 bit patterns."""
    fx = s["fx"]
    if grp == "a_proj.fp8":
        v = fx["attn_norm"]
    elif grp == "wq_b":
        v = fx["qr"]
    elif grp.startswith("wo_a.g"):
        g = int(grp[len("wo_a.g"):])
        v = np.asarray(fx["o"], F).reshape(8, -1)[g]
    elif grp == "wo_b":
        v = fx["z"]
    elif grp in ("router", "shared_gu") or grp.endswith(".gu"):
        v = fx["ffn_norm"]
    elif grp == "shared.w2":
        v = next(e["a"] for e in s["experts"] if e["weight"] is None)
    elif grp.endswith(".w2"):
        ex = int(grp.split(".")[0][3:])
        v = next(e["a"] for e in s["experts"] if e["prefix"].endswith(f"experts.{ex}."))
    else:
        raise KeyError(grp)
    cols = {tuple(m["cols"]) for m in mats}
    assert len(cols) == 1, (grp, cols)
    c0, c1 = cols.pop()
    v = np.asarray(v, F).reshape(-1)[c0:c1]
    import hdc_golden as G
    return G.bits(v).astype(np.uint32)


def cmd_fplan(a):
    import gzip
    import dsrom_1m_field as FD
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    snaps = load_snaps(Path(a.golden))
    sm = json.loads((FD.S81 / "stage_map.json").read_text())
    rb, bfs = sm["region_bounds"], set(sm["BF_site_IDs"])
    need = {st: sorted({e for r in range(ROWS) for e in snaps[(st, r)]["router"]["ids"]}) for st in range(STAGES)}
    allx = set().union(*need.values())
    base = []
    with gzip.open(FD.S81 / "matrix_map.jsonl.gz", "rt") as f:
        for ln in f:
            r = json.loads(ln)
            if r["layer"] == 0 and (r["expert"] is None or r["expert"] in allx):
                base.append(r)
    phases, xs = [], {}
    for st in range(STAGES):
        ents = [_mtp_entry(e, st) for e in base if e["expert"] is None or e["expert"] in need[st]]
        for grp, (node, _xsrc, mats) in FD.layer_groups(0, ents, rb, bfs).items():
            K = mats[0]["K"]
            bf = mats[0]["fmt"] == "bf16"
            out = "fp32" if (bf or grp == "wo_b") else "bf16"
            groups = []
            for mm in mats:
                if groups and not any(FD.illegal(groups[-1] + [mm], r) for r in range(128)):
                    groups[-1].append(mm)
                else:
                    groups.append([mm])
            batched = grp in FIELD_BATCHED or grp.startswith("wo_a.g")
            if batched:
                rows_pos = [list(range(ROWS))]
            else:                                   # a routed expert: a one-position phase per row that chose it
                ex = int(grp.split(".")[0][3:])
                rows_pos = [[r] for r in range(ROWS) if ex in snaps[(st, r)]["router"]["ids"]]
            for gi, g in enumerate(groups):
                bad = [r for r in range(128) if FD.illegal(g, r)]
                assert not bad, (st, grp, bad[:4])
                gname = f"S{st}.{grp}" + ("" if len(groups) == 1 else "." + "+".join(x["alias"] for x in g))
                for rows in rows_pos:
                    name = gname + ("" if batched else f".r{rows[0]}")
                    phases.append(dict(stage=st, layer=40 + st, node=node, group=grp, phase=name, mats_key=gname,
                                       rows=rows, positions=len(rows), K=K, out=out,
                                       fmts=sorted({m["fmt"] for m in g}), mats=g,
                                       regions=sorted({int(r) for m in g for r in m["regions"]})))
                    xs[name] = np.stack([field_x(snaps[(st, r)], grp, g) for r in rows])
    np.savez(work / "x.npz", **xs)
    plan = dict(schema="opentallas.dsrom-1m.draft-blocks.field-plan.v1", stages=STAGES, rows=ROWS, rank=0,
                experts=need, region_bounds=rb, bf_sites=sorted(bfs), phases=phases,
                placement="S81 canonical L0 placement re-targeted to mtp.{st} (rank 0); gate: first 32 rank rows",
                x_sha256={k: hashlib.sha256(v.tobytes()).hexdigest() for k, v in xs.items()})
    (work / "plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    print(len(phases), "phases,", sum(len(p["regions"]) for p in phases), "region runs")
    return 0


def cmd_fextract(a):
    import v41_die_field as VF
    from rtl_v41_rom_array import Ckpt
    work = Path(a.work).resolve()
    plan = json.loads((work / "plan.json").read_text())
    ck = Ckpt(Path(a.snapshot))
    (work / "mats").mkdir(exist_ok=True)
    done = set()
    for ph in plan["phases"]:
        if ph["mats_key"] in done:
            continue
        done.add(ph["mats_key"])
        arr = {}
        for i, m in enumerate(ph["mats"]):
            (r0, r1), (c0, c1) = m["rows"], m["cols"]
            x = VF.mat(ck, m["tensor"], m["fmt"], r1 - r0, c1 - c0, r0, c0)
            if m["fmt"] == "bf16":
                arr[f"{i}.u16"] = x.u16
            else:
                arr[f"{i}.exp"] = x.exp
                arr[f"{i}.{'codes' if m['fmt'] == 'fp8' else 'nib'}"] = x.codes if m["fmt"] == "fp8" else \
                    x.nib.astype(np.uint8)
        np.savez(work / "mats" / f"{ph['mats_key']}.npz", **arr)
    (work / "mats" / "checkpoint.json").write_text(json.dumps(dict(revision=Path(a.snapshot).resolve().name,
                                                                   header_sha256=ck.pins)) + "\n")
    print(len(done), "matrix slice files")
    return 0


def cmd_fbuild(a):
    import dsrom_1m_field as FD
    return FD.cmd_build(argparse.Namespace(work=Path(a.work), jobs=a.jobs))


def region_image_np(work, ph, reg, rb, bfs, xs, img: Path, OBASE=32768):
    """tools/dsrom_1m_field.region_image with P positions: x of position p at XBASE + p*K, rows of position p
    expected at OBASE + p*nrows + row (the spine's obase + p*ops)."""
    import dsrom_1m_field as FD
    import hdc_golden_v41 as G
    import v41_die_images_w17w10 as I
    pairs = list(range(rb[reg], rb[reg + 1]))
    bfp = [p for p in pairs if p in bfs]
    qp = [p for p in pairs if p not in bfs]
    qslots = [s for s in range(FD.NP) if s not in FD.BF_SLOTS]
    slot = {p: FD.BF_SLOTS[i] for i, p in enumerate(bfp)} | {p: qslots[i] for i, p in enumerate(qp)}
    fld = I.Field(FD.NP, FD.NR, FD.NBF, pp=True, fast=True)
    mats, gmap = [], []
    for mm, full in zip(ph["mats"], FD.full_mats(work, dict(phase=ph["mats_key"], mats=ph["mats"]))):
        pl = mm["regions"].get(str(reg), [])
        if not pl:
            continue
        srows = sorted({s for s, _, _ in pl})
        loc = {s: j for j, s in enumerate(srows)}
        rows = [r for s in srows for r in (2 * s, 2 * s + 1) if r < mm["entry_rows"]]
        sub = FD.take(full, rows)
        sub.s81_segments = mm["segments"]
        sub.s81_place = [(loc[s], seg, slot[p]) for s, seg, p in pl]
        mats.append(sub)
        gmap.append((mm, rows))
    fp32 = ph["out"] == "fp32"
    meta = I.add_phase(fld, mats, (fp32, fp32), 0)
    I.write_field(fld, img, FD.PHW)
    K, P = ph["K"], len(xs)
    nrows = meta["nrows"]
    assert FD.XBASE + P * K <= OBASE and OBASE + P * nrows <= (1 << FD.VAW)
    vm = np.zeros(1 << FD.VAW, dtype=np.uint32)
    for p, x in enumerate(xs):
        vm[FD.XBASE + p * K:FD.XBASE + (p + 1) * K] = x
    (img / "vm.hex").write_text("".join(f"{int(v):08x}\n" for v in vm))
    expect = {}
    for p, x in enumerate(xs):
        gold = I.golden_phase(mats, G.from_bits(x).astype(G.F))
        off = 0
        for (mm, rows), m in zip(gmap, mats):
            for i, r in enumerate(rows):
                f32, b16 = gold[off + i]
                expect[OBASE + p * nrows + off + i] = f32 if fp32 else (b16 << 16)
            off += m.rows
    meta = dict(nbeat=meta["nbeat"], t_read=meta["t_read"], t_phase_model=meta["t_phase_model"], nrows=nrows,
                segments_per_pair_max=meta["segments_per_pair_max"], pairs=len(pairs), bf_pairs=len(bfp))
    return meta, expect


def frun_one(args):
    work, ph, reg, rb, bfs, xs = args
    import hdc_golden_v41 as G
    G.set_arith("chunk8")
    rd = Path(work) / "runs" / ph["phase"] / f"r{reg:03d}"
    if rd.exists():
        shutil.rmtree(rd)
    img = rd / "img"
    img.mkdir(parents=True)
    t0 = time.time()
    OB = 32768
    meta, expect = region_image_np(work, ph, reg, rb, bfs, xs, img, OB)
    (rd / "ops.txt").write_text(f"0 {len(xs) - 1} 0 {ph['K']} {OB} {meta['nrows']}\n")
    t1 = time.time()
    p = subprocess.run([str(Path(work) / "build" / "tb"), str(img), str(rd / "ops.txt")], capture_output=True, text=True)
    t2 = time.time()
    lines = p.stdout.splitlines()
    writes = {}
    for ln in lines:
        t = ln.split()
        if t and t[0] == "W":
            writes.setdefault(int(t[2]), []).append(int(t[3], 16))
    opl = [ln for ln in lines if ln.startswith("OP ")]
    op = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", opl[0])} if opl else {}
    wrong = [ad for ad, v in expect.items() if writes.get(ad) != [v]]
    extra = [ad for ad in writes if ad not in expect]
    ok = p.returncode == 0 and bool(lines) and lines[-1].startswith("PASS") and not wrong and not extra
    res = dict(phase=ph["phase"], region=reg, pass_=ok, positions=len(xs), rows=len(expect), mismatched=len(wrong),
               extra=len(extra), first_mismatch=[(ad, writes.get(ad), expect[ad]) for ad in wrong[:3]], **meta,
               go=op.get("go"), first_w=op.get("first_w"), last_w=op.get("last_w"), idle=op.get("idle"),
               go_to_last_w=(op["last_w"] - op["go"]) if op.get("last_w", -1) >= 0 else None,
               go_to_idle=(op["idle"] - op["go"]) if op else None, image_s=round(t1 - t0, 2), sim_s=round(t2 - t1, 2),
               tail=lines[-1:] if lines else p.stderr[-300:])
    (rd / "result.json").write_text(json.dumps(res) + "\n")
    shutil.rmtree(img)
    return res


def cmd_frun(a):
    import concurrent.futures as cf
    work = Path(a.work).resolve()
    plan = json.loads((work / "plan.json").read_text())
    xz = np.load(work / "x.npz")
    rb, bfs = plan["region_bounds"], set(plan["bf_sites"])
    only = set(a.only.split(",")) if a.only else None
    tasks = []
    for ph in plan["phases"]:
        if only and not any(ph["phase"].startswith(o) for o in only):
            continue
        regs = ph["regions"] if not a.regions else [r for r in ph["regions"] if r in set(map(int, a.regions.split(",")))]
        for reg in regs:
            if not a.force and (work / "runs" / ph["phase"] / f"r{reg:03d}" / "result.json").exists():
                continue
            tasks.append((str(work), ph, reg, rb, bfs, list(xz[ph["phase"]])))
    tasks.sort(key=lambda t: (t[1]["mats_key"], t[1]["phase"], t[2]))
    print(f"{len(tasks)} region runs", flush=True)
    bad = 0
    with cf.ProcessPoolExecutor(a.jobs) as ex:
        for i, r in enumerate(ex.map(frun_one, tasks, chunksize=4)):
            bad += not r["pass_"]
            if not r["pass_"] or i % 200 == 0:
                print(i, r["phase"], r["region"], "PASS" if r["pass_"] else "FAIL", r["rows"], r["go_to_last_w"],
                      r["go_to_idle"], r["sim_s"], r["tail"], r["first_mismatch"], flush=True)
    print("failed", bad)
    return 1 if bad else 0


# ======================================================================================================================
# su: the stream-unit chains, 5 rows op-major (tools/dsrom_1m_su.py lowering), ot_hdc_v41x_vec N1024/M256
# ======================================================================================================================
def chain_route_k(VC, I, c, rt, route_scale):
    """dsrom_1m_su.chain_route at the DSpark router's shape: 128 scores + bias, top-3 weights."""
    from dsrom_1m_su import f32u
    n, k = len(rt["scores"]), len(rt["ids"])
    S_ = c.vm(rt["scores"])
    bias = c.crom(rt["bias"])
    BI = c.buf(n)
    c.op(nout=1, nin=n, abase=S_, aso=n, asi=1, csrc=I.SRC_CLO, cbase=bias, cso=n, csi=1, ad=I.AD_C, obase=BI,
         oso=n, osi=1)                                                                                         # 0
    c.check("scores + bias (the select's input)", BI, rt["biased"])
    IX = c.vm_u32(np.asarray(rt["ids"], np.uint32))
    TOT = c.buf(8)
    c.op(nout=1, nin=k, abase=S_, asi=1, aso=k, aind=I.IND_I, aibase=IX, red=I.RED_SUM, redwhole=1, rbase=TOT,
         dst=0)                                                                                                # 1
    DEN = c.buf(8)
    c.op(nout=1, nin=1, abase=TOT, ad=I.AD_IMM, imm2=f32u(1e-20), obase=DEN)                                   # 2
    W = c.buf(8)
    c.op(nout=1, nin=k, abase=S_, asi=1, aso=k, aind=I.IND_I, aibase=IX, bbase=DEN, m1=I.M1_DIVB,
         e1=I.E1_MULIMM, imm2=f32u(route_scale), obase=W, oso=k, osi=1)                                        # 3
    c.check("route weights", W, rt["weights"])
    return [("ffn.bias", 0, "write"), ("ffn.weights", 3, "write")]


def su_chain_fns(S, B, VC, I):
    """{chain: (fn(c, snap) -> nodes, op_major)}: op_major chains run the 5 rows op j by op j (the program's
    merged slots); the attention softmax is the program's serial section: one chain per row."""
    import hdc_golden_v41 as V

    def hc_mix(which):
        return lambda c, s: [(f"{which}.{n}", k, e) for n, k, e in S.chain_hc_mix(B, VC, I, c, s["hc"][f"hc.{which}"])]

    def hc_pre_norm(which, i):
        def f(c, s):
            hp = s["hc"]["hc_pre"][i]
            w = s["attn_norm_w"] if which == "attn" else s["ffn_norm_w"]
            want = V.rmsnorm_bf16(hp["out"], w, s["eps"])
            assert same(want, s["fx"]["attn_norm" if which == "attn" else "ffn_norm"])
            return [(f"{which}.{n}", k, e) for n, k, e in S.chain_hc_pre_norm(B, VC, I, c, hp["h"], hp["pre"], w, want)]
        return f

    def hc_post(which, i):
        return lambda c, s: [(f"{which}.{n}", k, e) for n, k, e in S.chain_hc_post(B, VC, I, c, s["hc"]["hc_post"][i])]

    def q_norm(c, s):
        return S.chain_rmsnorm(B, VC, I, c, s["q_norm"], "attn.q_norm")[1]

    def kv_norm_rope(c, s):
        y, nodes = S.chain_rmsnorm(B, VC, I, c, s["kv_norm"], "attn.kv_norm")
        T_ = c.buf(64)
        S.lower_rope_rows(c, I, y, 1, 512, s["kv_rope"]["cs"], out=T_)
        c.check("kv RoPE tail (pre FP8 QDQ)", T_, np.asarray(s["kv_rope"]["out"])[-64:])
        return nodes + [("attn.kv_rope_qdq:rope", 3, "write")]

    def q_rope(c, s):
        Q = c.vm(s["q_rope"]["x"])
        T_ = c.buf(HEADS_DIE * 64)
        S.lower_rope_rows(c, I, Q, HEADS_DIE, 512, s["q_rope"]["cs"], out=T_)
        c.check("q RoPE tails, 16 heads", T_, s["q_rope"]["out"][:, -64:])
        return [("attn.q_rope", 0, "write")]

    def attend(c, s):
        return [(f"attn.{n}", k, e) for n, k, e in S.chain_attend(B, VC, I, c, s["hc"]["attend"])]

    return {
        "attn.hc_mix": (hc_mix("attn"), True), "attn.hc_pre_norm": (hc_pre_norm("attn", 0), True),
        "attn.q_norm": (q_norm, True), "attn.kv_norm_rope": (kv_norm_rope, True), "attn.q_rope": (q_rope, True),
        "attn.softmax": (attend, False), "attn.hc_post": (hc_post("attn", 0), True),
        "ffn.hc_mix": (hc_mix("ffn"), True), "ffn.hc_pre_norm": (hc_pre_norm("ffn", 1), True),
        "ffn.router_act": (lambda c, s: S.chain_router_act(B, VC, I, c, s["router"]), True),
        "ffn.route": (lambda c, s: chain_route_k(VC, I, c, s["router"], s["route_scale"]), True),
        "ffn.swiglu": (lambda c, s: S.chain_swiglu(B, VC, I, c, s["experts"], s["limit"], routed=True), True),
        "ffn.shared_swiglu": (lambda c, s: S.chain_swiglu(B, VC, I, c, s["experts"], s["limit"], routed=False), True),
        "ffn.route_w": (lambda c, s: S.chain_route_w(B, VC, I, c, s["experts"], s["limit"]), True),
        "ffn.hc_post": (hc_post("ffn", 1), True)}


def cmd_suprep(a):
    import dshbm_baseline_measure as B
    import dsrom_1m_su as S
    import hdc_golden as G
    import hdc_isa_v41 as I
    import rtl_hdc_v41x_vec_campaign as VC
    out = Path(a.out)
    snaps = load_snaps(out / "golden" if (out / "golden").exists() else out)
    cases = []
    for st in range(STAGES):
        for name, (fn, op_major) in su_chain_fns(S, B, VC, I).items():
            groups = [list(range(ROWS))] if op_major else [[r] for r in range(ROWS)]
            for rows in groups:
                c = B.Chain(f"S{st}.{name}" + ("" if op_major else f".r{rows[0]}"), VC)
                s0 = snaps[(st, rows[0])]
                c.eps, c.hc_eps = s0["eps"], s0["hc_eps"]
                per = []
                for r in rows:
                    n0 = len(c.ops)
                    nodes = fn(c, snaps[(st, r)])
                    per.append((n0, len(c.ops) - n0, nodes))
                k = per[0][1]
                assert all(p[1] == k for p in per), (name, [p[1] for p in per])
                R = len(rows)
                if R > 1:            # issue op j of every row before op j + 1 (a row's ops keep their order)
                    c.ops = [c.ops[r * k + j] for j in range(k) for r in range(R)]
                nodes = [dict(node=n, op=j * R + R - 1, ops=[j * R + r for r in range(R)], event=ev)
                         for n, j, ev in per[0][2]]
                c.meta = dict(layer=f"S{st}", stage=st, fn=name, rows=rows, op_major=R > 1, nodes=nodes)
                cases.append(dict(name=c.name, meta=c.meta, init=c.init, cr_lo=c.cr_lo, cr_hi=c.cr_hi, ops=c.ops,
                                  checks=[(lab, ad, G.bits(w).astype(np.uint32), "golden") for lab, ad, w, _k in
                                          c.checks]))
    h = hashlib.sha256()
    for st in range(STAGES):
        for r in range(ROWS):
            h.update((out / "golden" / f"snap_S{st}_r{r}.pkl").read_bytes())
    (out / "su_cases.pkl").write_bytes(pickle.dumps(dict(cases=cases, snapshots_sha256=h.hexdigest())))
    print("cases", len(cases))
    return 0


def cmd_surun(a):
    import dsrom_1m_su as S
    return S.cmd_run(argparse.Namespace(variant=a.variant, out=a.out, cases="su_cases.pkl", n=1024, m=256,
                                        fp=a.fp, work=a.work))


# ======================================================================================================================
# quant: ot_hdc_actquant (one instance) on the 5 rows' quantiser inputs; select: ot_hdc_select K 3 on 128 scores
# ======================================================================================================================
def quant_inputs(snaps, st):
    rows = 2304 // TP
    lo, hi = DIE * rows, (DIE + 1) * rows
    cat = lambda f: np.concatenate([np.asarray(f(snaps[(st, r)]), F).reshape(-1) for r in range(ROWS)])  # noqa: E731
    return {
        "attn.quant": cat(lambda s: s["fx"]["attn_norm"]),
        "attn.q_quant": cat(lambda s: s["q_norm"]["out"]),
        "attn.z_quant": cat(lambda s: np.asarray(s["fx"]["z"])[DIE * 2048:(DIE + 1) * 2048]),
        "ffn.quant": cat(lambda s: s["fx"]["ffn_norm"]),
        "ffn.quant2": cat(lambda s: np.concatenate([e["a"][lo:hi] for e in s["experts"] if e["weight"] is not None])),
        "ffn.shared_quant": cat(lambda s: np.concatenate([e["a"][lo:hi] for e in s["experts"] if e["weight"] is None])),
        "attn.kv_rope_qdq": cat(lambda s: s["kv_rope"]["out"])}


def cmd_quant(a):
    import hdc_golden_v41 as V
    import rtl_hdc_v41_blockdot_campaign as BC
    import dsrom_1m_su as S
    out = Path(a.out)
    snaps = load_snaps(out / "golden")
    work = (out / "quant_work").resolve()
    work.mkdir(parents=True, exist_ok=True)
    verilator = os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
    exe = work / "obj" / "Vtb_dsrom_1m_quant"
    if not exe.exists():
        subprocess.run([verilator, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module",
                        "tb_dsrom_1m_quant", "-Mdir", str(work / "obj"), *map(str, S.QUANT_RTL), *map(str, BC.LIB),
                        str(S.QUANT_TB)], check=True, capture_output=True)
    rows = []
    for st in range(STAGES):
        for node, x in quant_inputs(snaps, st).items():
            blocks = x.reshape(-1, 32)
            d = work / f"S{st}_{node}"
            d.mkdir(exist_ok=True)
            ys = []
            with open(d / "aq_in.mem", "w") as fi, open(d / "aq_exp.mem", "w") as fe:
                for b in blocks:
                    fi.write(f"0{BC.hexw(V.bits(b), 32):0256x}\n")
                    f_, e, codes, y = BC.aq_expect(b, False)
                    ys.append(np.asarray(y, np.uint32))
                    fe.write(f"{f_:01x}{e & 0xFFF:03x}{BC.hexw(codes, 8):064x}{BC.hexw(y, 16):0128x}\n")
            golden_ok = same(V.qdq_fp8(x), (np.concatenate(ys) << 16).view(F))
            r = subprocess.run([str(exe), f"+NAQ={len(blocks)}"], cwd=d, capture_output=True, text=True).stdout
            m = re.search(r"DSQ naq=(\d+) checked=(\d+) errors=(\d+) nq4=(\d+) checked=(\d+) errors=(\d+) "
                          r"first_in=(-?\d+) last_out=(-?\d+)", r)
            naq, ca, ea, nq4, cb, eb, fi_, lo_ = map(int, m.groups())
            cyc = lo_ - fi_ + 1
            rows.append(dict(stage=st, node=node, rows=ROWS, elements=int(len(x)), beats=len(blocks),
                             unit="ot_hdc_actquant", cycles_one_instance=cyc, latency_after_stream=cyc - len(blocks),
                             us=round(cyc / CLK * 1e6, 5), clock="1.2 GHz streaming (as su.json quant rows)",
                             exact=bool("PASS" in r and ea == 0 and ca == len(blocks) and golden_ok)))
            print(st, node, len(blocks), cyc, rows[-1]["exact"], flush=True)
    res = dict(schema="opentallas.dsrom-1m.draft-blocks.quant.v1", generated_utc=now(), rows=rows,
               status="pass" if all(r["exact"] for r in rows) else "fail",
               source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (*S.QUANT_RTL, S.QUANT_TB)})
    (out / "quant.json").write_text(json.dumps(res, indent=1) + "\n")
    print("QUANT", res["status"])
    return 0 if res["status"] == "pass" else 1


def cmd_select(a):
    import hdc_golden_v41 as V
    import rtl_hdc_v41_select_campaign as SC
    out = Path(a.out)
    snaps = load_snaps(out / "golden")
    work = out / "select_work"
    work.mkdir(parents=True, exist_ok=True)
    verilator = os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
    K, order = 3, 1
    obj = work / f"obj_K{K}_o{order}"
    if not (obj / "Vtb_hdc_select").exists():
        subprocess.run([verilator, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "--top-module", "tb_hdc_select",
                        f"-GK={K}", "-GVW=32", "-GIW=9", f"-GORDER={order}", "-Mdir", str(obj), str(SC.RTL),
                        str(SC.TB), str(SC.HARNESS), "-CFLAGS", "-O1"], check=True, capture_output=True)
    rows = []
    for st in range(STAGES):
        for r_ in range(ROWS):
            rt = snaps[(st, r_)]["router"]
            v = np.asarray(rt["biased"], F)
            golden = sorted(int(i) for i in V.topk_lowest_index(v, K))
            assert golden == rt["ids"]
            fin, fexp, n_el, n_out, h = SC.write_vectors([(v, list(range(len(v))), K)], K, 32, 9, order, work,
                                                         f"S{st}_r{r_}")
            o = subprocess.run([str(obj / "Vtb_hdc_select"), f"+IN={fin}", f"+EXP={fexp}", "+BUBBLE=0", "+GAP=0",
                                "+SEED=1"], capture_output=True, text=True).stdout
            rec = SC.parse(o)
            cyc = rec["elements"] - 1 + rec["latency_max"] + rec["outputs"]
            rows.append(dict(stage=st, row=r_, K=K, elements=rec["elements"], outputs=rec["outputs"],
                             latency_max=rec["latency_max"], cycles=cyc, us=round(cyc / CLK * 1e6, 5),
                             exact=bool(rec["pass"]), ids=golden, vectors_sha256=h))
            print(st, r_, cyc, rec["pass"], flush=True)
    res = dict(schema="opentallas.dsrom-1m.draft-blocks.select.v1", generated_utc=now(), rows=rows,
               status="pass" if all(r["exact"] for r in rows) else "fail",
               source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (SC.RTL, SC.TB, SC.HARNESS)})
    (out / "select.json").write_text(json.dumps(res, indent=1) + "\n")
    print("SELECT", res["status"])
    return 0 if res["status"] == "pass" else 1


# ======================================================================================================================
# attn: the full-geometry attention engine, 5 jobs (the serial rows) at T = 133 on the golden operands of die 0
# ======================================================================================================================
def kv_stored(V, row):
    """A golden FP8-QDQ KV row (BF16 values) in the engine's stored format: E4M3 codes + UE8M0 per 32 (the scale
    repeated for the two 16-element halves)."""
    row = np.asarray(row, F)
    q, e = V.quant_fp8(row)
    deq = V.to_bf16((q.reshape(-1, 32) * np.exp2(e)[:, None]).astype(F).reshape(-1))
    assert same(deq, row), "re-quantised row differs"
    table = {}
    for code in range(256):
        val = float(V.E4M3[code])
        if np.isfinite(val) and val not in table and not (val == 0 and code & 128):
            table[val] = code
    codes = np.array([table[float(x)] for x in q], dtype=np.int64)
    return codes, np.repeat(np.asarray(e, np.int64) + 127, 2)


def cmd_attn(a):
    import hdc_golden_v41 as V
    import rtl_hdc_v41x_attn_campaign as C
    out = Path(a.out)
    snaps = load_snaps(out / "golden")
    exe = Path(a.exe)
    res = dict(schema="opentallas.dsrom-1m.draft-blocks.attn.v1", generated_utc=now(), stages={},
               executable_sha256=C.sha(exe), engine="ot_hdc_v41x_attn H16/D512/TD32/NL4 PWORDS 2 (NJOBMAX 6)",
               psup=a.psup)
    for st in range(STAGES):
        jobs = []
        for r in range(ROWS):
            at = snaps[(st, r)]["hc"]["attend"]
            kvm = at["kvm"]
            T, D = kvm.shape
            codes = np.zeros((T, D), np.int64)
            scales = np.zeros((T, D // 16), np.int64)
            for t in range(T):
                codes[t], scales[t] = kv_stored(V, kvm[t])
            p = V.to_bf16(at["e"])
            j = C.Job(at["q"], np.zeros(T, np.int64), codes, scales, p, f"DSpark mtp.{st} row {r}: golden q (die 0 "
                      f"heads), window 128 + block 5 rows, golden BF16 probabilities")
            sc, pv = j.expected()
            assert same(sc, at["s_raw"]) and same(pv, at["pv"]), "engine golden != draft golden"
            jobs.append(j)
        d = out / "attn_vectors" / f"S{st}"
        counts, stats = C.write_jobs(d, jobs, 16, 512, 32)
        t0 = time.time()
        r = subprocess.run([str(exe), f"+dir={d.resolve()}", f"+njob={ROWS}", "+seed=20261004", f"+psup={a.psup}"],
                           capture_output=True, text=True, timeout=7200)
        m = C.ENG_RE.search(r.stdout)
        assert m, r.stdout[-3000:]
        njob, scc, sce, pvc, pve, flt, lsmax, lsmin, lpmax, cyc, tmo = map(int, m.groups())
        per = [dict(zip(("job", "T", "qk_first", "qk_last", "qk_beats", "pv_first", "pv_last", "pv_beats",
                         "last_score", "last_p", "last_pv"), map(int, g.groups()))) for g in C.JOB_RE.finditer(r.stdout)]
        prev = 0
        for pj in per:
            pj["position_cycles"] = pj["last_pv"] - prev
            prev = pj["last_pv"]
        exact = (r.returncode == 0 and sce == 0 and pve == 0 and njob == ROWS and scc == stats["scores"] and
                 pvc == stats["pv"] and flt == stats["score_faults"] + stats["pv_faults"] and not tmo)
        res["stages"][f"S{st}"] = dict(T=T, jobs=njob, scores_checked=scc, score_errors=sce, pv_checked=pvc,
                                       pv_errors=pve, faults=flt, total_cycles=cyc, per_job=per, exact=exact,
                                       counts=counts, wall_s=round(time.time() - t0, 1))
        print(st, cyc, exact, [(p_["last_score"], p_["last_pv"]) for p_ in per], flush=True)
    res["status"] = "pass" if all(v["exact"] for v in res["stages"].values()) else "fail"
    (out / "attn.json").write_text(json.dumps(res, indent=1) + "\n")
    print("ATTN", res["status"])
    return 0 if res["status"] == "pass" else 1


# ======================================================================================================================
# links: the stage hop at the 5-row residual and the TP4 collectives at the 5-row payloads (tools/dsrom_1m_links.py
# benches, imported unchanged; only the payload list differs)
# ======================================================================================================================
DRAFT_COLL = [
    ("draft.a_allgather", "all_gather", ROWS * 3648),         # wq_a | wkv rows of the 5 rows (L0's 3,648 B a row)
    ("draft.router_allgather", "all_gather", ROWS * 128 * 4),  # 128 FP32 router scores a row
    ("draft.allreduce_row", "all_reduce", 20480),               # one row's attention-out / MoE-combine partial sums
    ("draft.rows_allgather", "all_gather", 67584),              # the 128 window rows (as L0)
]
# 12 descriptors: the gathers, five all-reduces back to back (the 5 rows: 102,400 B exceed one descriptor's 320
# words a rank), then repeats
DRAFT_OPS = [DRAFT_COLL[0], DRAFT_COLL[1]] + [DRAFT_COLL[2]] * 5 + [DRAFT_COLL[3], DRAFT_COLL[0], DRAFT_COLL[1],
                                                                     DRAFT_COLL[2], DRAFT_COLL[3]]


def cmd_links(a):
    import dsrom_1m_links as L
    out = Path(a.out)
    work = out / "links_work"
    work.mkdir(parents=True, exist_ok=True)
    res = dict(schema="opentallas.dsrom-1m.draft-blocks.links.v1", generated_utc=now())
    if a.part in ("hop", "all"):
        nb = ROWS * L.RESIDUAL_B
        r = L.run_hop_case(work, ("hop5_lfec_fanout", dict(FB=64, CH=L.CH_LFEC, CHU=L.CH_UCIE), nb,
                                  "DSpark stage hop: the 5 block rows' residual (5 x 40,976 B)"))
        f = r["fields"]
        phy = L.phy_Bps()
        phy_cyc = nb / phy * CLK
        phy_extra = max(0, int(np.ceil(phy_cyc - f["flits"] - 1e-9))) if phy_cyc > f["flits"] else 0
        wire = 2 * L.SERDES_STAGES
        tot = f["last_flit"] + phy_extra + wire
        res["hop"] = dict(exact=r["exact"], payload_B=nb, payload_flits=f["flits"], link_rt_first_to_last_cycles=f["last_flit"],
                          vendor_channel_cycles=dict(board=L.CH_LFEC, ucie_fanout=L.CH_UCIE),
                          measured_endpoint_cycles=f["last_flit"] - L.CH_LFEC - L.CH_UCIE,
                          phy_serialization_ns=round(nb / phy * 1e9, 2), phy_serialization_extra_cycles=phy_extra,
                          wire_stage_cycles=wire, total_cycles=tot, us=round(tot / CLK * 1e6, 4), summary=r["summary"],
                          sources={p: sha(ROOT / p) for p in L.HOP_RTL})
        print("hop", res["hop"]["total_cycles"], res["hop"]["us"], r["exact"], flush=True)
    if a.part in ("coll", "all"):
        L.S81_COLL[:] = DRAFT_COLL
        L.S81_OPS[:] = DRAFT_OPS
        assert len(L.S81_OPS) == L.NOPS
        c = L.cmd_coll(argparse.Namespace(work=str(work / "coll"), configs="s81_r0d1024", ncal=a.ncal,
                                          nmeas=a.nmeas, jobs=a.jobs))
        rec = c["configs"]["s81_r0d1024"]
        res["collectives"] = rec["by_collective"]
        res["collectives_all_runs_passed"] = rec["all_runs_passed"]
        res["coll_sources"] = c.get("sources")
        res["coll_fixture"] = c["fixture"]
    (out / f"links_{a.part}.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    print("LINKS", json.dumps({k: v for k, v in res.items() if k in ("hop",)}, default=str)[:400])
    return 0


# the recovery placement's die-to-die messages (one row each, on the stage-hop endpoint ot_dsrom_link_rt + the same
# light-FEC / UCIe vendor budget and endpoint wire stages as the 5-row stage hop): name, bytes, role
RECOVERY_HOPS = [
    ("x_row", 10240, "ffn_norm x of one block row (5,120 BF16) primary rank die -> its expert replica die"),
    ("ids", 64, "one row's 3 routed expert ids (one flit) primary -> replica"),
    ("weights", 64, "one row's 3 FP32 route weights (one flit) primary -> replica"),
    ("ret_row", 5120, "one row's routed-expert sum, the rank's 1,280 output rows FP32, replica -> primary"),
]


def cmd_rlinks(a):
    """The recovery placement's messages measured on the stage-hop link RTL (same bench, case and budget rule as
    `links --part hop`; only the payload differs)."""
    import dsrom_1m_links as L
    out = Path(a.out)
    work = out / "rlinks_work"
    work.mkdir(parents=True, exist_ok=True)
    phy = L.phy_Bps()
    res = dict(schema="opentallas.dsrom-1m.draft-blocks.rlinks.v1", generated_utc=now(), source_commit=git_head(),
               rule="total = link_rt first input -> last flit delivered (measured RTL incl. the light-FEC/UCIe "
                    "vendor delay lines) + PHY serialisation beyond the endpoint's + 2 x 45 SerDes wire stages",
               hops={}, sources={p: sha(ROOT / p) for p in L.HOP_RTL})
    for name, nb, role in RECOVERY_HOPS:
        r = L.run_hop_case(work, (f"rec_{name}", dict(FB=64, CH=L.CH_LFEC, CHU=L.CH_UCIE), nb, role))
        f = r["fields"]
        phy_cyc = nb / phy * CLK
        phy_extra = max(0, int(np.ceil(phy_cyc - f["flits"] - 1e-9))) if phy_cyc > f["flits"] else 0
        wire = 2 * L.SERDES_STAGES
        tot = f["last_flit"] + phy_extra + wire
        res["hops"][name] = dict(role=role, exact=r["exact"], payload_B=nb, payload_flits=f["flits"],
                                 link_rt_first_to_last_cycles=f["last_flit"],
                                 vendor_channel_cycles=dict(board=L.CH_LFEC, ucie_fanout=L.CH_UCIE),
                                 measured_endpoint_cycles=f["last_flit"] - L.CH_LFEC - L.CH_UCIE,
                                 phy_serialization_extra_cycles=phy_extra, wire_stage_cycles=wire, total_cycles=tot,
                                 us=round(tot / CLK * 1e6, 4), summary=r["summary"])
        print(name, nb, tot, res["hops"][name]["us"], r["exact"], flush=True)
    res["status"] = "pass" if all(h["exact"] for h in res["hops"].values()) else "fail"
    (out / "rlinks.json").write_text(json.dumps(res, indent=1) + "\n")
    print("RLINKS", res["status"])
    return 0 if res["status"] == "pass" else 1


# ======================================================================================================================
# record: per-element measured times -> the block's fixed dependency graph (the S81 graph's sliding layer L0)
# ======================================================================================================================
SK_CLOCKS, SK_FMAX = 41, 151.9e6           # ot_hdc_sinkhorn (as tools/dsrom_1m_allmeasured_adapters.SINKHORN_UNIT_S)
QUANT_NET_SLOW = 22 + 15                   # quantiser hub network stages added arithmetically (as su.json wired_us)
SERIAL = ("scores", "max", "exp", "den", "sink", "pv", "normalize")
W_S81_PHASE = None                         # S81 floorplan field wire stages a phase (field.json convention)


def field_nodes(work: Path, plan, st):
    """Per graph node of stage st: measured cycles (phases in issue order, max over the die's regions; sum of
    go -> idle + 1 except the last + go -> last row write of the last) + S81 floorplan wire stages a phase."""
    fp = json.loads((ROOT / "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json").read_text())["trunk_stages"]
    import dsrom_1m_field as FD
    w = 2 * fp["stages_at_504"]["field_one_way"] - FD.BST_IN_VEHICLE
    nodes, phases = {}, []
    for ph in plan["phases"]:
        if ph["stage"] != st:
            continue
        rs = []
        for reg in ph["regions"]:
            f = work / "runs" / ph["phase"] / f"r{reg:03d}" / "result.json"
            rs.append(json.loads(f.read_text()) if f.exists() else None)
        done = [r for r in rs if r]
        complete = len(done) == len(rs)
        po = dict(phase=ph["phase"], node=ph["node"], positions=ph["positions"], rows=ph["rows"], K=ph["K"],
                  regions=len(rs), regions_run=len(done), complete=complete,
                  exact=complete and all(r["pass_"] for r in done), rows_checked=sum(r["rows"] for r in done),
                  go_to_last_row=max((r["go_to_last_w"] or 0) for r in done) if done else None,
                  go_to_idle=max((r["go_to_idle"] or 0) for r in done) if done else None)
        phases.append(po)
        nodes.setdefault(ph["node"], []).append(po)
    out = {}
    for n, ps in nodes.items():
        ok = all(p["go_to_last_row"] is not None for p in ps)
        meas = sum(p["go_to_idle"] + 1 for p in ps[:-1]) + ps[-1]["go_to_last_row"] if ok else None
        out[n] = dict(phases=[p["phase"] for p in ps], measured_cycles=meas, wire_cycles=w * len(ps),
                      cycles=None if meas is None else meas + w * len(ps),
                      us=None if meas is None else (meas + w * len(ps)) / CLK * 1e6,
                      rows_checked=sum(p["rows_checked"] for p in ps), exact=all(p["exact"] for p in ps),
                      complete=all(p["complete"] for p in ps))
    return out, phases, w


def field_unbatched(w):
    """The batched field nodes issued as 5 one-position sweeps: the L0 phases of field.json (same S81 placement and
    K, data-independent timing; rank 0; L0's gate is 96 rows a rank, the DSpark gate 32) x 5, + wire a phase."""
    fj = json.loads((AR_DIR / "field.json").read_text())
    per = {}
    for p in fj["phases"]:
        if p["layer"] != 0:
            continue
        if p["node"] in ("attn.a_proj", "attn.wq_b", "attn.wo_a", "attn.wo_b", "ffn.router", "ffn.shared_gu") or \
                (p["node"] == "ffn.down" and p["phase"].endswith("shared.w2")):
            per.setdefault(p["node"], []).append(p)
    out = {}
    for n, ps in per.items():
        seq = ps * ROWS
        cyc = sum(p["go_to_idle_cycles"] + 1 for p in seq[:-1]) + seq[-1]["go_to_last_row_cycles"] + w * len(seq)
        out[n if n != "ffn.down" else "ffn.down (shared w2 part)"] = dict(cycles=cyc, us=round(cyc / CLK * 1e6, 4),
                                                                         phases=len(seq))
    return out


def su_nodes(su, st, snaps_meta=None):
    """Per graph node: the wired increment over the previous node of its chain (op-major chains: a node completes
    when its op of the LAST row does), cycles at 0.9 GHz.  Softmax rows: per row."""
    from dsrom_1m_su import _completion
    out = {}
    for ch in su["chains"]:
        if ch["stage"] != st:
            continue
        prev = 0
        for nd in ch["nodes"]:
            comp = max(_completion(ch["per_op"][k], nd["event"]) for k in nd["ops"])
            key = nd["node"] if not ch["fn"] == "attn.softmax" else f"{nd['node']}.r{ch['rows'][0]}"
            out[key] = dict(cycles=comp - prev, us=(comp - prev) / SLOW * 1e6, chain=ch["chain"], exact=ch["exact"])
            prev = comp
    return out


def block_graph():
    """The S81 graph's L0 (sliding layer: window attention + MoE FFN) as the DSpark stage's fixed dependency
    graph: 'embed' -> the stage hop in; the serial attention section unrolled over the 5 rows (row r+1's q.k
    after row r's P.V on the in-order tile, its SU softmax after row r's normalise on the in-order SU); no substage
    hop (a DSpark stage fits one TP4 group); no Engram."""
    import dsrom_1m_measure as M
    g, _, _ = M.s58_graph()
    base = {}
    for n, nd in g.nodes.items():
        if n.startswith("L0."):
            base[n[3:]] = dict(deps=[d[3:] if d.startswith("L0.") else d for d in nd["deps"]],
                               model_us=(nd["issue"] + nd["depth"] + nd["ctrl"]) * 1e6, kind=nd.get("kind"),
                               desc=nd.get("desc"))
    base.pop("substage_hop0")
    for n, b in base.items():
        b["deps"] = ["hop_in" if d in ("embed", "substage_hop0") else d for d in b["deps"]]
        b["deps"] = ["attn.hc_post" if d == "substage_hop0" else d for d in b["deps"]]
    for n in ("ffn.hc.sumsq", "ffn.hc.fn", "ffn.hc_pre"):
        base[n]["deps"] = ["attn.hc_post" if d == "hop_in" else d for d in base[n]["deps"]]
    base["ffn.hc_post"]["deps"] = ["attn.hc_post" if d == "hop_in" else d for d in base["ffn.hc_post"]["deps"]]
    nodes = {"hop_in": dict(deps=[], model_us=0.4446, kind="hop")}
    for n, b in base.items():
        suf = n.split(".", 1)[1] if n.startswith("attn.") else None
        if suf in SERIAL:
            continue
        nodes[n] = dict(b)
    first_deps = base["attn.scores"]["deps"]
    for r in range(ROWS):
        for s in SERIAL:
            b = base[f"attn.{s}"]
            deps = [f"attn.{d.split('.', 1)[1]}.r{r}" if d.startswith("attn.") and d.split(".", 1)[1] in SERIAL
                    else d for d in b["deps"]]
            if s == "scores":
                deps = list(first_deps) if r == 0 else [f"attn.pv.r{r - 1}"]
            if s == "max" and r > 0:
                deps.append(f"attn.normalize.r{r - 1}")
            nodes[f"attn.{s}.r{r}"] = dict(deps=deps, model_us=b["model_us"], kind=b["kind"], desc=b["desc"])
    nodes["attn.wo_a"]["deps"] = [f"attn.normalize.r{ROWS - 1}"]
    return nodes


def longest(nodes, t):
    fin, via = {}, {}
    order = list(nodes)
    done = set()
    while len(done) < len(order):
        for n in order:
            if n in done or any(d not in done for d in nodes[n]["deps"]):
                continue
            st = max((fin[d] for d in nodes[n]["deps"]), default=0.0)
            via[n] = max(nodes[n]["deps"], key=lambda d: fin[d]) if nodes[n]["deps"] else None
            fin[n] = st + t[n]
            done.add(n)
    end = max(fin, key=fin.get)
    path, n = [], end
    while n:
        path.append(n)
        n = via[n]
    return fin[end], path[::-1], end


def cmd_record(a):
    out = Path(a.out)
    gold = json.loads((out / "golden" / "golden.json").read_text())
    plan = json.loads((out / "field" / "plan.json").read_text())
    su = json.loads((out / "su_N1024_M256_b22r15m5a4_dpi_beh.json").read_text())
    quant = json.loads((out / "quant.json").read_text())
    sel = json.loads((out / "select.json").read_text())
    attn = json.loads((out / "attn.json").read_text())
    hop = json.loads((out / "links_hop.json").read_text())["hop"]
    coll = json.loads((out / "links_coll.json").read_text()) if (out / "links_coll.json").exists() else None
    su_ar = json.loads((AR_DIR / "su.json").read_text())
    links_ar = json.loads((AR_DIR / "links.json").read_text())
    ar_nodes = dict(su_ar["nodes"]) if isinstance(su_ar["nodes"], list) else su_ar["nodes"]
    graph = block_graph()
    sk_us = SK_CLOCKS / SK_FMAX * 1e6
    blocks, per_stage, still = [], {}, []
    exact_all = gold["status"] == "pass"
    for st in range(STAGES):
        fn, fphases, w81 = field_nodes(out / "field", plan, st)
        sn = su_nodes(su, st)
        t, src = {}, {}

        def put(n, us, source, exact, cls="measured", modelled_us=0.0):
            t[n] = us
            src[n] = dict(us=round(us, 5), source=source, exact=exact, cls=cls, modelled_part_us=round(modelled_us, 5))

        put("hop_in", hop["us"], f"stage hop ot_dsrom_link_rt RTL at {hop['payload_B']} B (5 rows) "
                                 f"{hop['measured_endpoint_cycles']} cyc + light-FEC/UCIe VENDOR budget "
                                 f"{sum(hop['vendor_channel_cycles'].values())} cyc + 90 wire", hop["exact"],
            "measured+vendor_phy")
        for n, v in fn.items():
            put(n, v["us"], f"ROM field vehicle, {len(v['phases'])} phases ({', '.join(v['phases'][:3])}"
                            f"{'...' if len(v['phases']) > 3 else ''}), {v['rows_checked']} rows, + {v['wire_cycles']} "
                            f"S81 floorplan wire cyc", v["exact"] and v["complete"])
        # SU chains (wired), + the cited Sinkhorn unit a row, + the model's CDC crossing (modelled) as the AR does
        for n, v in sn.items():
            base = n.rsplit(".r", 1)[0] if re.search(r"\.r\d$", n) else n
            gname = n
            core = base.split(":")[0]
            cdc = ar_nodes.get(f"L0.{core}", {}).get("model_cdc_us", 0.0)
            if base.endswith(":front"):
                gname = core
                put(gname, v["us"] + ROWS * sk_us + cdc, f"{v['chain']}: SU front wired RTL {v['us']:.4f} us + "
                    f"ot_hdc_sinkhorn 41 clocks at 151.9 MHz x {ROWS} rows; CDC {cdc} modelled", v["exact"],
                    modelled_us=cdc)
                continue
            if base.endswith(":rope"):
                gname = core
                q = next(r for r in quant["rows"] if r["stage"] == st and r["node"] == core)
                qus = (q["cycles_one_instance"] + QUANT_NET_SLOW) / SLOW * 1e6
                put(gname, v["us"] + qus + cdc, f"{v['chain']}: RoPE wired RTL {v['us']:.4f} us + ot_hdc_actquant "
                    f"QDQ {q['cycles_one_instance']} cyc (+{QUANT_NET_SLOW} hub stages) on the 5 rows", v["exact"] and q["exact"],
                    modelled_us=cdc + QUANT_NET_SLOW / SLOW * 1e6)
                continue
            if re.search(r"\.r\d$", n):
                core = n.split(".r")[0]
                cdc = ar_nodes.get(f"L0.{core}", {}).get("model_cdc_us", 0.0)
                gname = f"{core}.r{n[-1]}"
            put(gname, v["us"] + cdc, f"{v['chain']}: wired RTL (BCAST 22 / RET 15) {v['us']:.4f} us"
                + (f"; CDC {cdc} modelled" if cdc else ""), v["exact"], modelled_us=cdc)
        for q in quant["rows"]:
            if q["stage"] != st or q["node"] == "attn.kv_rope_qdq":
                continue
            us = (q["cycles_one_instance"] + QUANT_NET_SLOW) / SLOW * 1e6
            put(q["node"], us, f"ot_hdc_actquant one instance, {q['beats']} blocks (5 rows) {q['cycles_one_instance']} "
                f"cyc at 0.9 GHz + {QUANT_NET_SLOW} hub network stages (added arithmetically, as su.json wired_us)",
                q["exact"], modelled_us=QUANT_NET_SLOW / SLOW * 1e6)
        srows = [r for r in sel["rows"] if r["stage"] == st]
        put("ffn.top6", 0.0, "inside ffn.top6_order (one unit, ascending output)", True)
        put("ffn.top6_order", sum(r["cycles"] for r in srows) / CLK * 1e6,
            f"ot_hdc_select K 3 on the 128 biased scores, {ROWS} rows one after another "
            f"({'+'.join(str(r['cycles']) for r in srows)} cyc)", all(r["exact"] for r in srows))
        aj = attn["stages"][f"S{st}"]
        prev = 0
        for r, j in enumerate(aj["per_job"]):
            put(f"attn.scores.r{r}", (j["last_score"] - prev) / CLK * 1e6,
                f"attention engine job {r} (T {aj['T']}): previous job's last P.V -> last score", aj["exact"])
            put(f"attn.pv.r{r}", (j["last_pv"] - j["last_score"]) / CLK * 1e6,
                f"attention engine job {r}: last score -> last P.V (P supplied by the bench)", aj["exact"])
            prev = j["last_pv"]
        # collectives
        if coll:
            cc = coll["collectives"]
            cex = coll["collectives_all_runs_passed"]
            put("attn.a_allgather", cc["draft.a_allgather"]["us"], f"tb_w15b_v41_tp4 S81 all_gather "
                f"{cc['draft.a_allgather']['payload_B']} B (5 rows)", cex)
            put("ffn.router_allgather", cc["draft.router_allgather"]["us"], f"tb_w15b_v41_tp4 S81 all_gather "
                f"{cc['draft.router_allgather']['payload_B']} B (5 rows x 128 FP32)", cex)
            put("attn.rows_allgather", cc["draft.rows_allgather"]["us"], "tb_w15b_v41_tp4 S81 all_gather 67,584 B "
                "(the 128 window rows, as L0)", cex)
            ar1 = cc["draft.allreduce_row"]
            for n in ("attn.out_allreduce", "ffn.combine_allreduce"):
                put(n, ROWS * ar1["us"], f"tb_w15b_v41_tp4 S81 all_reduce 20,480 B a row x {ROWS} rows issued one "
                    f"after another (102,400 B exceed one descriptor; max issue->commit {ar1['cycles']} cyc)", cex)
        missing = [n for n in graph if n not in t]
        for n in missing:
            if n.endswith("hc.fn"):
                us = ROWS * graph[n]["model_us"]
                t[n] = us
                src[n] = dict(us=round(us, 5), source=f"MODELLED: uarch node price {graph[n]['model_us']:.4f} us a row x "
                              f"{ROWS} (HE FP32 mixes [24, 20480]; no RTL bench, as in the AR composition)",
                              exact=None, cls="modelled", modelled_part_us=round(us, 5))
            else:
                raise SystemExit(f"stage {st}: no measurement for node {n}")
        tot, path, end = longest(graph, t)
        no_hop = tot - t["hop_in"]
        on = set(path)
        mod_on = sum(src[n]["modelled_part_us"] for n in path)
        exact_st = all(src[n]["exact"] in (True, None) for n in src)
        exact_all &= exact_st
        per_stage[f"mtp.{st}"] = dict(block_us=round(tot, 4), block_us_without_hop=round(no_hop, 4),
                                      critical_path=[dict(node=n, us=src[n]["us"], cls=src[n]["cls"]) for n in path],
                                      modelled_on_path_us=round(mod_on, 4), exact=exact_st,
                                      nodes=src, field_phases=fphases,
                                      experts=gold["stages"][f"mtp.{st}"]["experts"])
        blocks.append(tot)
        print(f"mtp.{st}: block {tot:.3f} us (no hop {no_hop:.3f}), modelled on path {mod_on:.3f}, exact {exact_st}")
    unb = field_unbatched(w81)
    for k in unb:                               # the same nodes as measured batched (np = 4), stage 0
        node = k.split(" ")[0]
        ps = [p for p in per_stage["mtp.0"]["field_phases"] if p["node"] == node and
              (node != "ffn.down" or p["phase"].endswith("shared.w2"))]
        cyc = sum(p["go_to_idle"] + 1 for p in ps[:-1]) + ps[-1]["go_to_last_row"] + w81 * len(ps)
        unb[k]["batched_np4_us_mtp0"] = round(cyc / CLK * 1e6, 4)
    rec = dict(
        schema="opentallas.dsrom-1m.draft-blocks.v1",
        basis=("full shape: the three DSpark blocks (mtp.0..2, 5 block rows, T = 128 window + 5 block rows) of the "
               "golden draft at the 1M anchor (position 1,048,575, y = the 1M reference token), every element measured "
               "in full-shape RTL on the released mtp.* weights and the golden's own activations, composed on the S81 "
               "graph's sliding-layer (L0) dependency structure with the serial attention section unrolled over the 5 "
               "rows. PLACEMENT (stated, not in the S81 binding: mtp.* is an unowned auxiliary obligation there): each "
               "DSpark stage on its own TP4 group of S81 layer-class dies, matrices on the S81 allocator's L0 placement "
               "(rank 0), one 5-row stage hop into each stage. ROM FIELD: the as-built W17 spine's multi-position phase "
               "(np = 4: one phase serves the 5 rows) for the batchable weight ops; routed experts one phase per row."),
        exact=bool(exact_all), block_us=[round(b, 4) for b in blocks], blocks_total_us=round(sum(blocks), 4),
        block5_us=round(sum(blocks) / len(blocks), 4),
        block5_us_without_hop=round(sum(per_stage[f"mtp.{s}"]["block_us_without_hop"] for s in range(STAGES)) / STAGES, 4),
        replaces=dict(block5_us=BLOCK5_REDUCED_US, basis="reduced-vehicle slice x transfer ratio "
                      "(results/rtl/dsrom_dspark_step_slices_20261004 / dsrom_fused_draft_head_20261004 l1_compose)"),
        nodes={k: v["nodes"] for k, v in per_stage.items()},
        stages={k: {kk: vv for kk, vv in v.items() if kk != "nodes"} for k, v in per_stage.items()},
        field_one_sweep_per_vector=dict(
            note="the batched field nodes issued as 5 one-position sweeps (the L0 phases of field.json: same "
                 "placement and K, data-independent timing) -- what np = 4 saves", nodes=unb),
        still_modelled=[
            dict(term="hc.fn (HE FP32 mixes [24, 20480], attn + ffn) x 5 rows", us=round(ROWS * graph["attn.hc.fn"]["model_us"], 4),
                 why="no HE/hc-engine RTL bench (also modelled in the AR composition); off the critical path unless "
                     "listed in critical_path"),
            dict(term="CDC fast->slow crossings on SU nodes", us=round(max(v["modelled_on_path_us"] for v in per_stage.values()), 4),
                 why="W18 ratio-FIFO latency, no CDC bench (as AR); includes the quantisers' 37 hub stages"),
            dict(term="light-FEC PHY (130 ns) + UCIe (10 ns) inside the stage hop", us=round(sum(hop["vendor_channel_cycles"].values()) / CLK * 1e6, 4),
                 why="VENDOR BUDGET (no PHY RTL), as AR"),
            dict(term="DSpark stage placement", us=None,
                 why="mtp.* is unowned in the S81 canonical binding; this uses L0's allocator placement on a dedicated "
                     "TP4 group (an owner mapping may differ)"),
            dict(term="older 127 window rows of each stage", us=None,
                 why="synthetic format-consistent (as the w17 1M state); timing is data-independent")],
        golden=dict(status=gold["status"], y=gold["y"], anchor=gold["anchor"], state=gold["state"],
                    stages=gold["stages"]),
        reference_ar=dict(hop_1row_us=links_ar["hop"]["per_hop_us"], allreduce_1row_cycles=links_ar["collectives"]["attn.out_allreduce"]["cycles"]),
        source_commit=git_head(), generated_utc=now(),
        inputs={**{f"remote:{p}": sha(out / p) for p in ("golden/golden.json", "field/plan.json",
                                                          "su_N1024_M256_b22r15m5a4_dpi_beh.json", "quant.json",
                                                          "select.json", "attn.json", "links_hop.json")},
                **({"remote:links_coll.json": sha(out / "links_coll.json")} if coll else {}),
                **{str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), AR_DIR / "field.json", AR_DIR / "su.json",
                                                              AR_DIR / "links.json",
                                                              ROOT / "tools/dsrom_1m_field.py", ROOT / "tools/dsrom_1m_su.py",
                                                              ROOT / "tools/dsrom_1m_links.py",
                                                              ROOT / "tools/dsrom_1m_measure.py",
                                                              ROOT / "tools/hdc_golden_v41.py")}})
    Path(a.record).write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print(json.dumps(dict(block_us=rec["block_us"], block5_us=rec["block5_us"], exact=rec["exact"],
                          total=rec["blocks_total_us"]), indent=0))
    return 0


# ======================================================================================================================
# recovery placement "DP1-EP5" (lever draft of the DS-ROM recovery): the three blocks' non-expert weights co-located
# on ONE TP4 primary group (no stage hop between blocks), each block's routed experts replicated on 5 expert TP4
# groups, replica r serving block row r (its 3 experts run concurrently with the other rows')
# ======================================================================================================================
REC_DIR = ROOT / "results/rtl/dsrom_recovery_20261004"
REC_DRAFT_DIR = REC_DIR / "draft"
PLACEMENT = REC_DRAFT_DIR / "placement.json"
PRIMARY_WORD_STRIDE = 1024          # block st's non-expert words in a pair start at st * 1,024 (L0 uses <= 888 a pair)
PAIR_WORDS = 8192
DIE_MM2_REF = "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json die.decision_priced_mm2"
REPLICAS = ROWS
NONBLOCK_HEAD = ("norm.weight", "markov_head.", "confidence_head.")
NONBLOCK_SEED = ("main_proj.", "main_norm.")


def _ckpt_headers(snap: Path, prefix="mtp."):
    idx = json.loads((snap / "model.safetensors.index.json").read_text())["weight_map"]
    files = sorted({f for k, f in idx.items() if k.startswith(prefix)})
    out = {}
    for fn in files:
        with open(snap / fn, "rb") as f:
            n = int.from_bytes(f.read(8), "little")
            h = json.loads(f.read(n))
        for k, v in h.items():
            if k.startswith(prefix):
                out[k] = dict(shape=v["shape"], dtype=v["dtype"], file=fn)
    return out


def cmd_placement(a):
    """The placement map: every released mtp.* tensor (2,401) and, for matrices, every rank row slice, homed once
    per replica.  In-die pairs: the S81 allocator's L0 placement (non-expert matrices: L0's pairs with block st's
    words at base st*1,024 + its offset in the pair; routed expert e: L0 expert e's pairs and bases)."""
    import gzip
    import dsrom_1m_field as FD
    hdr = _ckpt_headers(Path(a.snapshot))
    l0 = {}
    with gzip.open(FD.S81 / "matrix_map.jsonl.gz", "rt") as f:
        for ln in f:
            r = json.loads(ln)
            if r["layer"] == 0 and (r["expert"] is None or r["expert"] < 128):
                l0[r["alias"]] = r
    groups = [dict(group="draft.primary", dies=TP, role="attention, router, shared expert, hc mixes, norms and window "
                   "caches of mtp.0, mtp.1 and mtp.2 (one block at a time); mtp.0 seed projection")]
    groups += [dict(group=f"draft.mtp{st}.rep{r}", dies=TP, role=f"routed experts 0..127 of mtp.{st} (replica {r}: "
                    f"serves block row {r})") for st in range(STAGES) for r in range(REPLICAS)]
    words = {g["group"]: [0] * TP for g in groups}
    pair_use = {}                   # primary: (rank-invariant) pair -> words, to check the per-pair capacity
    tensors, n_rows = [], 0
    for name in sorted(hdr):
        h = hdr[name]
        parts = name.split(".")
        st = int(parts[1])
        sub = ".".join(parts[2:])
        rec = dict(tensor=name, shape=h["shape"], dtype=h["dtype"])
        if sub.startswith(NONBLOCK_HEAD):
            rec.update(home="head group (the draft head sweeps; head-term owner, unchanged)", slices=None)
            tensors.append(rec)
            continue
        if sub.endswith(".scale"):
            rec.update(home="with its weight's rows (UE8M0 block exponents carried in the element word)", slices=None)
            tensors.append(rec)
            continue
        m = re.fullmatch(r"ffn\.experts\.(\d+)\.(w[123])\.weight", sub)
        if m:
            e, w = int(m.group(1)), m.group(2)
            ent = l0[f"exp{e}.{w}"]
            sl = []
            for r in range(REPLICAS):
                g = f"draft.mtp{st}.rep{r}"
                for rank, rs in enumerate(ent["rank_slices"]):
                    nw = sum(c * wd for _, _, _, c, _, _, wd in ent["plans"])
                    words[g][rank] += nw
                    sl.append(dict(group=g, rank=rank, rows=rs["rows"], cols=rs["cols"], words=nw,
                                   in_die=f"S81 L0 exp{e}.{w} plans ({len(ent['plans'])} superrow runs, pairs and "
                                          f"bases as the S81 allocator placed them on the L0 stage-0 die)"))
            assert all(rs["rows"][0] == (0 if i == 0 else ent["rank_slices"][i - 1]["rows"][1])
                       for i, rs in enumerate(ent["rank_slices"])) and ent["rank_slices"][-1]["rows"][1] == h["shape"][0]
            n_rows += REPLICAS * h["shape"][0]
            rec.update(home="replicas", slices=sl)
            tensors.append(rec)
            continue
        alias = {"attn.wq_a.weight": ["wq_a"], "attn.wkv.weight": ["wkv"], "attn.wq_b.weight": ["wq_b.rows0", "wq_b.rows4608"],
                 "attn.wo_a.weight": ["wo_a.group0.rows0", "wo_a.group0.rows768", "wo_a.group1.rows0", "wo_a.group1.rows768"],
                 "attn.wo_b.weight": ["wo_b.rows0", "wo_b.rows4608"], "ffn.gate.weight": ["gate"],
                 "ffn.shared_experts.w1.weight": ["shared.w1"], "ffn.shared_experts.w3.weight": ["shared.w3"],
                 "ffn.shared_experts.w2.weight": ["shared.w2"]}.get(sub)
        if alias:
            sl = []
            for al in alias:
                ent = _mtp_entry(l0[al], st) if al == "gate" else l0[al]
                for rank, rs in enumerate(ent["rank_slices"]):
                    nw = sum(c * wd for _, _, _, c, _, _, wd in ent["plans"])
                    words["draft.primary"][rank] += nw
                    sl.append(dict(group="draft.primary", rank=rank, rows=rs["rows"], cols=rs["cols"], words=nw,
                                   in_die=f"S81 L0 {al} pairs, block words at base {st} x {PRIMARY_WORD_STRIDE} + "
                                          f"the entry's offset in the pair"))
                for _, pair, _, c, _, _, wd in ent["plans"]:     # one rank die's pairs (rank-invariant plans)
                    pair_use[(st, pair)] = pair_use.get((st, pair), 0) + c * wd
            # rows: the rank slices of all aliases partition the released rows exactly once
            area = sum((s["rows"][1] - s["rows"][0]) * (s["cols"][1] - s["cols"][0]) for s in sl)
            assert area == h["shape"][0] * h["shape"][1], (name, area, h["shape"])
            n_rows += h["shape"][0]
            rec.update(home="draft.primary", slices=sl)
            tensors.append(rec)
            continue
        if sub.startswith(NONBLOCK_SEED):
            rec.update(home="draft.primary (mtp.0 seed projection: the seed term, timing unchanged; rows split over "
                            "the 4 rank dies, pair placement not timed here)", slices=None)
            tensors.append(rec)
            continue
        rec.update(home="draft.primary, replicated on every rank die (vector / hc-mix store, as S81 holds L0's)",
                   slices=None)
        tensors.append(rec)
    # per-pair capacity on the primary: the three blocks' non-expert words stacked at st * 1,024
    per_pair = {}
    for (st, pair), w in pair_use.items():
        assert w <= PRIMARY_WORD_STRIDE, (st, pair, w)
        per_pair[pair] = max(per_pair.get(pair, 0), st * PRIMARY_WORD_STRIDE + w)
    assert max(per_pair.values()) <= PAIR_WORDS
    cap = 2417 * PAIR_WORDS
    fp = json.loads((ROOT / "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json").read_text())
    die_mm2 = fp["die"]["decision_priced_mm2"]
    n_dies = TP * len(groups)
    rec = dict(
        schema="opentallas.dsrom-recovery.draft-placement.v1", name="DP1-EP5", generated_utc=now(),
        source_commit=git_head(), checkpoint=Path(a.snapshot).resolve().name, mtp_tensors=len(hdr),
        rule=("each DSpark block's non-expert matrices (wq_a, wkv, wq_b, wo_a, wo_b, gate, shared w1/w3/w2) on ONE "
              "primary TP4 group for all three blocks (the S81 L0 rank slices and pairs; block st's words at base "
              "st x 1,024 of each pair), so block st+1 starts on the dies that hold block st's output (no stage "
              "hop); each block's 128 routed experts replicated on 5 expert TP4 groups (the S81 L0 rank slices and "
              "the L0 stage-0 die's pairs of expert e), replica r computing block row r's 3 experts and their sum "
              "in id order; every row of every released matrix placed once per replica"),
        groups=groups, dies=dict(primary=TP, expert_replicas=TP * STAGES * REPLICAS, total=n_dies,
                                 baseline_draft_dies=TP * STAGES, added_vs_baseline_draft=n_dies - TP * STAGES,
                                 die_mm2=die_mm2, die_mm2_source=DIE_MM2_REF,
                                 added_silicon_mm2=round((n_dies - TP * STAGES) * die_mm2, 1)),
        capacity=dict(pair_words=PAIR_WORDS, die_words=cap,
                      words_per_rank_die={g: max(v) for g, v in words.items() if g in ("draft.primary", "draft.mtp0.rep0")},
                      fill={g: round(max(v) / cap, 4) for g, v in words.items() if g in ("draft.primary", "draft.mtp0.rep0")},
                      primary_max_words_in_a_pair=max(per_pair.values())),
        links=dict(per_primary_rank_die=f"{STAGES * REPLICAS} replica links (one to rank r of each expert group, "
                                        "light-FEC board + UCIe class, the stage-hop endpoint ot_dsrom_link_rt); the "
                                        "baseline needed 2 stage links a block group",
                   note="a star of 15 board links per primary die: port count beyond the S81 die's stage links is "
                        "an added link-endpoint area not yet priced in the die floorplan"),
        matrix_rows_placed=n_rows, tensors=tensors)
    PLACEMENT.parent.mkdir(parents=True, exist_ok=True)
    Path(a.record).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(tensors=len(tensors), dies=rec["dies"], capacity={k: v for k, v in rec["capacity"].items()
                                                                            if k != "words_per_rank_die"}), indent=1))
    return 0


def _serial_us(phases, w):
    """field_nodes' rule: phases back to back on one die (go -> idle + 1 except the last, + go -> last row write of
    the last) + S81 floorplan wire stages a phase."""
    cyc = sum(p["go_to_idle"] + 1 for p in phases[:-1]) + phases[-1]["go_to_last_row"] + w * len(phases)
    return cyc / CLK * 1e6, cyc


def recovery_graph():
    """block_graph() re-wired for DP1-EP5: the routed-expert chain runs per row on its replica; the shared w2 stays
    on the primary; the combine waits for every row's returned sum and the shared w2."""
    g = block_graph()
    moved = ("ffn.experts_gu", "ffn.swiglu", "ffn.route_w", "ffn.quant2", "ffn.down")
    for n in moved:
        g.pop(n)
    for n, nd in g.items():
        assert not any(d in moved for d in nd["deps"]) or n == "ffn.combine_allreduce", (n, nd["deps"])
    g["ffn.shared_down"] = dict(deps=["ffn.shared_quant"], kind="matvec")
    for r in range(ROWS):
        g[f"ffn.x_hop.r{r}"] = dict(deps=["ffn.norm.scale"], kind="hop")
        g[f"ffn.rquant.r{r}"] = dict(deps=[f"ffn.x_hop.r{r}"], kind="vector")
        g[f"ffn.ids_hop.r{r}"] = dict(deps=["ffn.top6_order"], kind="hop")
        g[f"ffn.w_hop.r{r}"] = dict(deps=["ffn.weights"], kind="hop")
        g[f"ffn.experts_gu.r{r}"] = dict(deps=[f"ffn.rquant.r{r}", f"ffn.ids_hop.r{r}"], kind="matvec")
        g[f"ffn.swiglu.r{r}"] = dict(deps=[f"ffn.experts_gu.r{r}"], kind="vector")
        g[f"ffn.route_w.r{r}"] = dict(deps=[f"ffn.swiglu.r{r}", f"ffn.w_hop.r{r}"], kind="vector")
        g[f"ffn.quant2.r{r}"] = dict(deps=[f"ffn.route_w.r{r}"], kind="vector")
        g[f"ffn.down.r{r}"] = dict(deps=[f"ffn.quant2.r{r}"], kind="matvec")
        g[f"ffn.ret_hop.r{r}"] = dict(deps=[f"ffn.down.r{r}"], kind="hop")
    g["ffn.combine_allreduce"]["deps"] = [f"ffn.ret_hop.r{r}" for r in range(ROWS)] + ["ffn.shared_down"]
    return g


def cmd_recovery(a):
    base = json.loads(Path(a.base).read_text())
    rl = json.loads(Path(a.rlinks).read_text())
    pl = json.loads(Path(a.placement).read_text())
    assert base["exact"] and rl["status"] == "pass"
    hops = rl["hops"]
    fpj = json.loads((ROOT / "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json").read_text())["trunk_stages"]
    import dsrom_1m_field as FD
    w = 2 * fpj["stages_at_504"]["field_one_way"] - FD.BST_IN_VEHICLE
    g0, g = block_graph(), recovery_graph()
    stages, blocks, per_node = {}, [], {}
    for st in range(STAGES):
        bn = base["nodes"][f"mtp.{st}"]
        t0 = {n: v["us"] for n, v in bn.items()}
        tot0, _, _ = longest(g0, t0)
        assert abs(tot0 - base["block_us"][st]) < 1e-3, (st, tot0, base["block_us"][st])   # the record recomposes
        ph = base["stages"][f"mtp.{st}"]["field_phases"]
        assert all(p["exact"] and p["complete"] for p in ph)
        src = {n: dict(v) for n, v in bn.items() if n not in ("ffn.experts_gu", "ffn.swiglu", "ffn.route_w",
                                                              "ffn.quant2", "ffn.down")}

        def put(n, us, source, exact=True, cls="measured", mod=0.0):
            src[n] = dict(us=round(us, 5), source=source, exact=exact, cls=cls, modelled_part_us=round(mod, 5))
        if st > 0:
            put("hop_in", 0.0, f"DP1-EP5: mtp.{st} sits on the primary group that holds mtp.{st - 1}'s output "
                               "(residual already in every rank die's hub VM): no stage hop", True, "placement")
        sh = [p for p in ph if p["phase"].endswith("shared.w2")]
        us, cyc = _serial_us(sh, w)
        put("ffn.shared_down", us, f"ROM field vehicle (as-built record) phase {sh[0]['phase']} np 4, {cyc} cyc incl. "
                                   f"{w} S81 wire, on the primary")
        for r in range(ROWS):
            gu = [p for p in ph if p["node"] == "ffn.experts_gu" and p["rows"] == [r]]
            dn = [p for p in ph if p["node"] == "ffn.down" and p["rows"] == [r]]
            assert len(gu) == len(dn) == 3, (st, r, len(gu), len(dn))
            ugu, cgu = _serial_us(gu, w)
            udn, cdn = _serial_us(dn, w)
            put(f"ffn.experts_gu.r{r}", ugu, f"ROM field vehicle (as-built record) phases {', '.join(p['phase'] for p in gu)} "
                                            f"back to back on replica {r} (identical image: L0 expert pairs), {cgu} cyc incl. "
                                            f"{3 * w} S81 wire")
            put(f"ffn.down.r{r}", udn, f"ROM field vehicle (as-built record) phases {', '.join(p['phase'] for p in dn)} "
                                       f"back to back on replica {r}, {cdn} cyc incl. {3 * w} S81 wire")
            for n, key in (("swiglu", "ffn.swiglu"), ("route_w", "ffn.route_w"), ("quant2", "ffn.quant2"),
                           ("rquant", "ffn.quant")):
                b = bn[key]
                put(f"ffn.{n}.r{r}", b["us"], f"UPPER BOUND: the 5-row measured {key} ({b['source']}) charged to "
                                              f"replica {r}'s one row", b["exact"], b["cls"], b["modelled_part_us"])
            for n, hk in (("x_hop", "x_row"), ("ids_hop", "ids"), ("w_hop", "weights"), ("ret_hop", "ret_row")):
                hh = hops[hk]
                put(f"ffn.{n}.r{r}", hh["us"], f"ot_dsrom_link_rt RTL at {hh['payload_B']} B ({hh['role']}): "
                                               f"{hh['measured_endpoint_cycles']} cyc endpoint + light-FEC/UCIe VENDOR "
                                               f"budget {sum(hh['vendor_channel_cycles'].values())} cyc + "
                                               f"{hh['wire_stage_cycles']} wire", hh["exact"], "measured+vendor_phy",
                    sum(hh["vendor_channel_cycles"].values()) / CLK * 1e6)
        t = {n: v["us"] for n, v in src.items()}
        missing = [n for n in g if n not in t]
        assert not missing, missing
        tot, path, _ = longest(g, t)
        ex = all(v["exact"] in (True, None) for v in src.values())
        stages[f"mtp.{st}"] = dict(block_us=round(tot, 4), baseline_block_us=base["block_us"][st], exact=ex,
                                   critical_path=[dict(node=n, us=src[n]["us"], cls=src[n]["cls"]) for n in path],
                                   modelled_on_path_us=round(sum(src[n]["modelled_part_us"] for n in path), 4),
                                   nodes=src)
        blocks.append(tot)
        old = {n: v["us"] for n, v in bn.items()}
        per_node[f"mtp.{st}"] = dict(
            hop_in=[old["hop_in"], src["hop_in"]["us"]],
            experts_gu=[old["ffn.experts_gu"], max(src[f"ffn.experts_gu.r{r}"]["us"] for r in range(ROWS))],
            down=[old["ffn.down"], max(max(src[f"ffn.down.r{r}"]["us"] for r in range(ROWS)), src["ffn.shared_down"]["us"])],
            added_hops_on_path=round(sum(src[n]["us"] for n in path if "_hop." in n), 4),
            block=[base["block_us"][st], round(tot, 4)])
        print(f"mtp.{st}: {base['block_us'][st]:.4f} -> {tot:.4f} us exact {ex}")
    total = round(sum(blocks), 4)
    rec = dict(
        schema="opentallas.dsrom-1m.draft-blocks.v1", variant="recovery DP1-EP5",
        basis=("the as-built full-shape draft-block measurement (results/rtl/dsrom_1m_allmeasured_20261004/"
               "draft_blocks.json: every element exact vs the golden draft at the 1M anchor) recomposed on the DP1-EP5 "
               "placement (results/rtl/dsrom_recovery_20261004/draft/placement.json): blocks co-located on one primary "
               "TP4 group (no stage hop into mtp.1 / mtp.2), routed experts on 5 row replicas per block (each "
               "replica's 3 phases are the measured phases of the identical L0-pair image), + the replica messages "
               "measured on the stage-hop link RTL (rlinks.json)"),
        exact=all(s["exact"] for s in stages.values()), block_us=[round(b, 4) for b in blocks], blocks_total_us=total,
        baseline_blocks_total_us=base["blocks_total_us"], per_node_old_new_us=per_node, stages=stages,
        rlinks=hops, placement=dict(record=str(Path(a.placement).resolve().relative_to(ROOT)), sha256=sha(a.placement),
                                    name=pl["name"], dies=pl["dies"]),
        still_modelled=base["still_modelled"] + [
            dict(term="replica SU nodes (swiglu, route_w, quant2, quant) of ONE row", us=None,
                 why="charged at the measured 5-row op-major time (an upper bound: the replica issues a subset)")],
        source_commit=git_head(), generated_utc=now(),
        inputs={str(Path(p).resolve().relative_to(ROOT)): sha(p) for p in (a.base, a.rlinks, a.placement, __file__)})
    Path(a.record).write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print(json.dumps(dict(blocks=rec["block_us"], total=total, baseline=base["blocks_total_us"], exact=rec["exact"])))
    return 0


# ======================================================================================================================
# main
# ======================================================================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("golden")
    p.add_argument("--out", required=True)
    p.add_argument("--snapshot", type=Path, default=SNAP_DEFAULT)
    p.add_argument("--ref", default=str(REF_DEFAULT))
    for n in ("fplan", "fextract", "fbuild", "frun"):
        p = sp.add_parser(n)
        p.add_argument("--work", required=True)
        p.add_argument("--golden")
        p.add_argument("--snapshot", type=Path, default=SNAP_DEFAULT)
        p.add_argument("--jobs", type=int, default=32)
        p.add_argument("--only")
        p.add_argument("--regions")
        p.add_argument("--force", action="store_true")
    for n in ("suprep", "surun", "quant", "select", "attn"):
        p = sp.add_parser(n)
        p.add_argument("--out", required=True)
        p.add_argument("--variant", default="wired", choices=("unit", "wired"))
        p.add_argument("--fp", default="dpi_beh")
        p.add_argument("--work")
        p.add_argument("--exe")
        p.add_argument("--psup", type=int, default=2)
    p = sp.add_parser("record")
    p.add_argument("--out", required=True)
    p.add_argument("--record", default=str(REC))
    p = sp.add_parser("links")
    p.add_argument("--out", required=True)
    p.add_argument("--part", default="all", choices=("hop", "coll", "all"))
    p.add_argument("--ncal", type=int, default=24)
    p.add_argument("--nmeas", type=int, default=12)
    p.add_argument("--jobs", type=int, default=16)
    p = sp.add_parser("rlinks")
    p.add_argument("--out", required=True)
    p = sp.add_parser("placement")
    p.add_argument("--snapshot", type=Path, default=SNAP_DEFAULT)
    p.add_argument("--record", default=str(PLACEMENT))
    p = sp.add_parser("recovery")
    p.add_argument("--base", default=str(REC))
    p.add_argument("--rlinks", default=str(REC_DRAFT_DIR / "rlinks.json"))
    p.add_argument("--placement", default=str(PLACEMENT))
    p.add_argument("--record", default=str(REC_DRAFT_DIR / "draft_blocks_recovery.json"))
    a = ap.parse_args()
    return {"golden": cmd_golden, "fplan": cmd_fplan, "fextract": cmd_fextract, "fbuild": cmd_fbuild,
            "frun": cmd_frun, "suprep": cmd_suprep, "surun": cmd_surun, "quant": cmd_quant, "select": cmd_select,
            "attn": cmd_attn, "links": cmd_links, "record": cmd_record, "rlinks": cmd_rlinks,
            "placement": cmd_placement, "recovery": cmd_recovery}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
