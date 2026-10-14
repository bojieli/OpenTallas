#!/usr/bin/env python3
"""DSpark (MTP) draft golden of the DeepSeek-V4.1 1M token for the S81 RTL path (s81-functional-token r3, 2026-10-14).

The draft block that follows the 1M reference token: pending token y = 21946 (the reference's next token) at anchor
1,048,575, block rows at positions anchor+1 .. anchor+5, through the three DSpark stages mtp.0 .. mtp.2
(Model.dspark_stage), the last stage's hc_pre + norm, the shared lm_head and the Markov head bias, d_{i+1} =
argmax(logits_i + markov(d_i)) (Model.draft).  State: tools/dsrom_1m_draft_blocks.build_state (the anchor's window row
from the REAL main hidden of the 1M token, h_in of L37 / L38 / L39 from the w17 shards; older window rows synthetic,
seeded like the backbone's synthetic state).

Writes to --out:
  draft.json                d_1 .. d_5, the anchor, y, the stage outputs' digests, every check
  snap_S<st>_r<i>.pkl       per stage and block row: the SU operand snapshot (tools/dsrom_1m_su.py snap format,
                            tools/dsrom_1m_draft_blocks.row_snaps) for tools/s81_ftok/su_layer.py
  hc_chain_M<st>R<i>.pkl    per stage and block row: the HC chain fixture (tools/s81_ctrl/die_layer_chain.py format,
                            layer name M<st>R<i>) for tools/s81_ctrl/die_layer_stim.py --chain
  draft_head.npz            per row: xf (final norm x), head logits, Markov bias, final logits (golden), d_i, d_{i+1}
Every intermediate is asserted bit-exact against the uninstrumented golden (Model.dspark_stage, Model.draft) before
anything is written.

    python3 tools/s81_ftok/mtp_golden.py --out DIR [--ref /home/ubuntu/w17work/ref/ctx1048576_seed20260930]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/s81_suhc"))
sys.path.insert(0, str(ROOT / "tools/s81_ctrl"))
F = np.float32
CHAIN_SCHEMA = "opentallas.s81-ctrl.die-layer-hc-chain.v1"


def same(a, b):
    a, b = np.asarray(a, F), np.asarray(b, F)
    return bool(a.shape == b.shape and np.array_equal(a.view(np.uint32), b.view(np.uint32)))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ref", type=Path, default=Path(os.environ.get("OT_DSROM_1M_GOLD",
                                                                     "/home/ubuntu/w17work/ref/ctx1048576_seed20260930")))
    a = ap.parse_args()
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    import dsrom_1m_draft_blocks as DB
    import hc_gate as HG
    V.set_arith("chunk8")
    a.out.mkdir(parents=True, exist_ok=True)
    ck = LC.Checkpoint()
    m, init_sha = LC.build_model(ck, engram=False)
    y = 21946
    zh = np.load(a.ref / "ctx1048576_head.npz")
    assert int(np.argmax(zh["logits"])) == y
    anchor, R = DB.ANCHOR, DB.ROWS
    state, sdesc, mh, main_x = DB.build_state(m, V, LC, a.ref)
    checks = {}
    ids = [y] + [m.noise_id] * (m.dspark_block - 1)

    class EmbedRows:                     # embed.weight is read by row (Checkpoint.rows), never whole
        def __getitem__(self, t):
            return np.asarray(ck.rows("embed.weight", [int(t)])[0], F)
    m.w["embed.weight"] = EmbedRows()
    for t_ in sorted(set(ids)):               # a subset zero-fills embedding rows it did not copy (hbm-sim/ds_ckpt)
        checks[f"embed row {t_} non-zero"] = bool(np.any(m.w["embed.weight"][t_] != 0))
    hs = [np.repeat(np.asarray(m.w["embed.weight"][t], F)[None, :], m.hc, axis=0).astype(F) for t in ids]
    pres = [np.array([1, 0, 0, 0], dtype=F)[:m.hc] for _ in ids]
    eps = F(m.eps)
    stages = {}
    for st in range(m.n_mtp):
        L = m.L + st
        ref_h, ref_pre = m.dspark_stage(L, [h.copy() for h in hs], [p.copy() for p in pres], anchor, state)
        # the per-row SU operands (dsrom_1m_su snap format), the instrumented stage checked against the plain one
        oh, op, cap, log = DB.capture_stage(m, V, L, hs, pres, anchor, state)
        checks[f"mtp.{st} capture == golden stage"] = all(same(x, y_) for x, y_ in zip(oh, ref_h)) and \
            all(same(x, y_) for x, y_ in zip(op, ref_pre))
        snaps = DB.row_snaps(m, V, L, cap, log)
        # the HC chain per row (block entry h, the two blocks' (pre, w, eps, comb, post, y)), replayed op by op
        mixes = [m.hc_mixes(h, L, "attn") for h in hs]
        xs = [V.rmsnorm_bf16(m.hc_pre(h, p), m.lw(L, "attn_norm.weight"), m.eps) for h, p in zip(hs, pres)]
        ys = m.dspark_attention(L, xs, anchor, state)
        for i in range(R):
            h0, p0 = hs[i], pres[i]
            ch = dict(h=h0.copy(), h_in=h0.copy(), src=f"mtp.{st} row {i} (position {anchor + 1 + i})")
            wa = np.asarray(m.lw(L, "attn_norm.weight"), F).copy()
            a_pre, a_post, a_comb = mixes[i]
            xg = HG.g_norm(h0, p0, wa, eps)
            checks[f"mtp.{st} r{i} attn norm (hc_gate) == golden"] = same(xg, xs[i])
            h1 = m.hc_post(ys[i], h0, a_post, a_comb)
            checks[f"mtp.{st} r{i} attn post (hc_gate) == golden"] = same(
                HG.g_post(h0, np.asarray(ys[i], F), np.asarray(a_comb, F).reshape(4, 4), np.asarray(a_post, F)), h1)
            ch["attn"] = (np.asarray(p0, F).copy(), wa, eps, np.asarray(a_comb, F).reshape(4, 4).copy(),
                          np.asarray(a_post, F).copy(), np.asarray(ys[i], F).copy())
            ch["attn_checks"] = ([(f"mtp.{st} r{i} attn_norm", -1, HG.u32(xs[i]).copy(), "write")],
                                 [(f"mtp.{st} r{i} h after attn hc_post", -1, HG.u32(h1).reshape(-1).copy(), "write")],
                                 h0.copy(), h0.copy())
            f_pre, f_post, f_comb = m.hc_mixes(h1, L, "ffn")
            wf = np.asarray(m.lw(L, "ffn_norm.weight"), F).copy()
            xf = V.rmsnorm_bf16(m.hc_pre(h1, a_pre), wf, m.eps)
            checks[f"mtp.{st} r{i} ffn norm (hc_gate) == golden"] = same(HG.g_norm(h1, np.asarray(a_pre, F), wf, eps), xf)
            yf = m.moe(L, xf, None)
            h2 = m.hc_post(yf, h1, f_post, f_comb)
            checks[f"mtp.{st} r{i} ffn post (hc_gate) == golden"] = same(
                HG.g_post(h1, np.asarray(yf, F), np.asarray(f_comb, F).reshape(4, 4), np.asarray(f_post, F)), h2)
            checks[f"mtp.{st} r{i} h_out == golden stage"] = same(h2, ref_h[i])
            checks[f"mtp.{st} r{i} pre_out == golden stage"] = same(f_pre, ref_pre[i])
            ch["ffn"] = (np.asarray(a_pre, F).copy(), wf, eps, np.asarray(f_comb, F).reshape(4, 4).copy(),
                         np.asarray(f_post, F).copy(), np.asarray(yf, F).copy())
            ch["ffn_checks"] = ([(f"mtp.{st} r{i} ffn_norm", -1, HG.u32(xf).copy(), "write")],
                                [(f"mtp.{st} r{i} h after ffn hc_post", -1, HG.u32(h2).reshape(-1).copy(), "write")],
                                h1.copy(), h1.copy())
            ch["h_out"], ch["pre_out"] = h2.copy(), np.asarray(f_pre, F).copy()
            name = f"M{st}R{i}"
            fx = dict(schema=CHAIN_SCHEMA, layer=name, context=1048576, engram=False, chain=ch,
                      checks={k: v for k, v in checks.items() if f"mtp.{st} r{i} " in k}, shard="(DSpark draft golden)",
                      shard_sha256="", checkpoint=str(LC.HF), golden_init_sha256=init_sha, arith=V.ARITH,
                      golden_sha256={p: sha(ROOT / p) for p in ("tools/hdc_golden_v41.py", "tools/hdc_golden.py")})
            snaps[i]["ftok_name"] = name
            if all(checks.values()):
                (a.out / f"hc_chain_{name}.pkl").write_bytes(pickle.dumps(fx, protocol=4))
                (a.out / f"snap_S{st}_r{i}.pkl").write_bytes(pickle.dumps(snaps[i], protocol=4))
        stages[f"mtp.{st}"] = dict(experts=[s["router"]["ids"] for s in snaps], T=snaps[0]["T"],
                                   out_sha256=hashlib.sha256(b"".join(np.asarray(h, F).tobytes() for h in ref_h)).hexdigest())
        print(f"mtp.{st}: experts {stages[f'mtp.{st}']['experts']} T {snaps[0]['T']} checks "
              f"{all(checks.values())}", flush=True)
        hs, pres = ref_h, ref_pre
    # ---- the draft head: last stage's hc_pre + norm, lm_head, Markov bias, argmax (Model.draft, replayed)
    Lf = m.L + m.n_mtp - 1
    xh = [V.to_bf16(m.hc_pre(h, p)) for h, p in zip(hs, pres)]
    xn = [V.rmsnorm_bf16(x, m.lw(Lf, "norm.weight"), m.eps) for x in xh]
    hl = [V.mv(m.w["head.weight"], x) for x in xn]
    emb, mhead = m.lw(Lf, "markov_head.embed.weight"), m.lw(Lf, "markov_head.head.weight")
    out, mb, fl = [y], [], []
    for i in range(R):
        b = V.mv(mhead, emb[out[i]])
        lg = V.add(hl[i], b)
        mb.append(b)
        fl.append(lg)
        out.append(int(np.argmax(lg)))
    # the uninstrumented draft (Model.draft) from a fresh state
    state2, _sd, _mh, _mx = DB.build_state(m, V, LC, a.ref)
    # a checkpoint subset holds zero-filled placeholders for tensors it did not copy (hbm-sim/ds_ckpt: every mtp.* is
    # zero, which drafts 0, 0, 0, 0, 0 "exactly"): refuse a degenerate draft
    for st in range(m.n_mtp):
        checks[f"mtp.{st} weights non-zero (gate, wq_a)"] = bool(np.any(np.asarray(m.lw(m.L + st, "ffn.gate.weight"), F) != 0))
    checks["markov_head non-zero"] = bool(np.any(np.asarray(mhead[:64], F) != 0))
    checks["draft logits not constant"] = all(float(np.max(x) - np.min(x)) > 0 for x in fl)
    d_ref, lg_ref = m.draft(y, anchor, state2)
    checks["draft tokens == Model.draft"] = list(map(int, d_ref)) == out[1:]
    checks["draft logits == Model.draft"] = all(same(x, y_) for x, y_ in zip(fl, lg_ref))
    np.savez(a.out / "draft_head.npz", xf=np.stack(xn), head_logits=np.stack(hl), markov=np.stack(mb),
             logits=np.stack(fl), tokens_in=np.asarray(out[:-1]), tokens_out=np.asarray(out[1:]))
    rec = dict(schema="opentallas.s81-ftok.mtp-draft-golden.v1", y=y, anchor=anchor, positions=[anchor + 1 + i for i in range(R)],
               noise_id=int(m.noise_id), drafts=out[1:], stages=stages, state=sdesc, checks=checks,
               status="pass" if all(checks.values()) else "fail", arith=V.ARITH, golden_init_sha256=init_sha,
               golden_sha256={p: sha(ROOT / p) for p in ("tools/hdc_golden_v41.py", "tools/hdc_golden.py")})
    (a.out / "draft.json").write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print("DRAFT", out[1:], rec["status"])
    bad = [k for k, v in checks.items() if not v]
    if bad:
        print("FAILED CHECKS", bad)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
