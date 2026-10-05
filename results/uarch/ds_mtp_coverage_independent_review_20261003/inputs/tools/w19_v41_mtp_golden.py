#!/usr/bin/env python3
"""Golden reference of one full-shape DeepSeek-V4.1-Flash MTP VERIFY pass at 1M (W19, the HBM comparator's token).

    HDC_V41_ARITH=chunk8 python3 tools/w19_v41_mtp_golden.py --out /home/ubuntu/w19work/mtp [--layers 0-39]

The verify pass is the golden's own Model.forward_positions order (layer-major: every position through layer L before
any through L + 1), run with Model.layer on the W17 reference state (tools/rtl_v41_fullshape_layer_campaign
.synthetic_state, seed 20260930, context 1,048,576) so that position 0 is exactly the reference token's position
(1,048,575, input token 16754, next token 21946).  The block is DSpark's: the pending token y = 16754 followed by
dspark_block_size = 5 draft tokens at positions 1,048,576 .. 1,048,580.  The drafts are fixed (not drafted here):
d1 = 21946 (the reference's next token, so the first draft is accepted) and d2..d5 = the reference position's next
four logits (103774, 113689, 93642, 33100).  Each position carries its own window row, compressor slot, index
selection, candidate blocks and top-6 experts (W11 forward_positions semantics), so the pass measures the union of
routed experts a verify pass fetches.

Writes, per layer, mtp_L{LL}.npz (every position's h_in / pre_in / traces / appended rows, suffixed @j) and .json
(experts per position, the union, digests), and mtp_head.npz / mtp_head.json (every position's logits and argmax).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402
import rtl_v41_fullshape_layer_campaign as LC  # noqa: E402
from hdc_golden import F  # noqa: E402

REF = ROOT / "results/rtl/w17_v41_1m_reference_token.json"
DRAFTS = [21946, 103774, 113689, 93642, 33100]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--layers", default="0-39")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    ref = json.loads(REF.read_text())
    ctx, seed = ref["context"], ref["seed"]
    a0, _, b0 = a.layers.partition("-")
    layers = list(range(int(a0), int(b0 or a0) + 1))
    assert layers[0] == 0
    t0 = time.time()
    ck = LC.Checkpoint()
    m, init_sha = LC.build_model(ck, engram=True)
    full = layers == list(range(m.L))
    st, sdesc = LC.synthetic_state(m, ctx, seed=seed, layers=list(range(m.L)) if full else layers)
    if full and sdesc["state_sha256"] != ref["state"]["state_sha256"]:
        raise SystemExit("synthetic state differs from the reference record")
    print(f"model + state {time.time() - t0:.0f} s, rss {LC.rss_gb():.1f} GB", flush=True)
    hist = LC.token_history(ctx, seed=seed)
    assert hist == ref["token_history"]
    st["tokens"] = list(hist)
    tokens = [hist[-1]] + DRAFTS
    pos0 = ctx - 1
    st["tokens"].extend(DRAFTS)
    n0 = len(hist) - 1
    ctxs = [{"pos": pos0 + j, "hist": st["tokens"][:n0 + j + 1],
             "h": np.repeat(ck.rows("embed.weight", [t]), m.hc, axis=0).astype(F),
             "pre": np.array([1, 0, 0, 0], dtype=F)} for j, t in enumerate(tokens)]
    pin = LC.golden_pin()
    summary = []
    for L in layers:
        t1 = time.time()
        rec = {"layer": L, "positions": [c["pos"] for c in ctxs], "tokens": tokens, "golden": pin, "arith": V.ARITH}
        arrs, exps = {}, []
        for j, cx in enumerate(ctxs):
            grew = {s: len(st["ckv"][s]) for s in m.kv_src}
            arrs[f"h_in@{j}"], arrs[f"pre_in@{j}"] = cx["h"].copy(), cx["pre"].copy()
            tr = {}
            m.layer(L, cx, st, tr)
            arrs[f"h_out@{j}"], arrs[f"pre_out@{j}"] = cx["h"], cx["pre"]
            for k, v in tr.items():
                if not isinstance(v, list):
                    arrs[f"{k}@{j}"] = v
            arrs[f"win{L}@{j}"] = st["win"][L][-1]
            for s in m.kv_src:
                if len(st["ckv"][s]) != grew[s]:
                    arrs[f"ckv{s}@{j}"], arrs[f"ik{s}@{j}"] = st["ckv"][s][-1], st["ik"][s][-1]
            e = list(map(int, tr.get(f"L{L}.experts", [])))
            exps.append(e)
            if f"L{L}.index_select" in tr:
                rec.setdefault("index_select_sha256", {})[str(j)] = hashlib.sha256(
                    np.asarray(tr[f"L{L}.index_select"], np.int64).tobytes()).hexdigest()
        rec["experts"] = exps
        rec["union_experts"] = sorted(set(x for e in exps for x in e))
        rec["n_union"] = len(rec["union_experts"])
        rec["digests"] = {k: LC.digest(v) for k, v in arrs.items()}
        rec["wall_s"] = round(time.time() - t1, 1)
        np.savez_compressed(a.out / f"mtp_L{L:02d}.npz", **arrs)
        (a.out / f"mtp_L{L:02d}.json").write_text(json.dumps(rec, indent=1) + "\n")
        for k in [k for k in m.w if k.startswith(f"layers.{L}.")]:
            del m.w[k]
        summary.append(rec["n_union"])
        print(f"L{L:02d}: union {rec['n_union']} experts, {rec['wall_s']} s, rss {LC.rss_gb():.1f} GB", flush=True)
    if layers[-1] == m.L - 1:
        lgs, out = [], []
        for cx in ctxs:
            xf = V.rmsnorm_fold(m.hc_pre(cx["h"], cx["pre"]), m.w["norm.weight"], m.eps)
            lg = V.mv(m.w["head.weight"], xf)
            lgs.append(lg)
            out.append(int(np.argmax(lg)))
        np.savez_compressed(a.out / "mtp_head.npz", **{f"logits@{j}": lg for j, lg in enumerate(lgs)})
        acc = 0
        while acc < len(DRAFTS) and DRAFTS[acc] == out[acc]:
            acc += 1
        head = {"targets": out, "drafts": DRAFTS, "accepted": acc,
                "logits_sha256": [LC.digest(lg) for lg in lgs],
                "position0_matches_reference": out[0] == ref["next_token"] and LC.digest(lgs[0]) == ref["logits_sha256"],
                "mean_union_experts": float(np.mean(summary)), "init_sha256": init_sha,
                "wall_s": round(time.time() - t0, 1), "peak_rss_gb": round(LC.rss_gb(), 2)}
        (a.out / "mtp_head.json").write_text(json.dumps(head, indent=1) + "\n")
        print(json.dumps(head), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
