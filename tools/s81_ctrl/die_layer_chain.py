#!/usr/bin/env python3
"""HC golden chain of ONE DeepSeek-V4.1 layer at the 1M token for tb_s81_die_layer, for layers the pinned su_cases
pickle does not hold (L14, an Engram layer): a SEPARATE small fixture, the pinned pickle is never touched.

Built on the checkpoint host from the RELEASED checkpoint + the w17 1M golden shard (no synthetic operand):
  h_in   = shard h_in (the layer-entry 4-copy residual: the HIDDEN payload);
  h      = Model.engram_layer(h_in) for an Engram layer, asserted == shard L<L>.engram (the h the attn block reads);
  attn   : pre = shard pre_in, w = attn_norm.weight, eps, (a_pre, post, comb) = Model.hc_mixes(h, L, "attn"),
           y = shard L<L>.attn;  ffn: pre = a_pre, w = ffn_norm.weight, hc_mixes(h1, L, "ffn"), y = shard L<L>.ffn.
Asserted bit for bit before anything is written, with BOTH the golden model (rmsnorm_fold(hc_pre), hc_post) and the
bench's own reference (hc_gate.g_norm / g_post): norm output == shard L<L>.attn_norm / L<L>.ffn_norm, final h ==
shard h_out == block<L>, the ffn pre mix == shard pre_out.

The fixture is a pickle {schema, layer, chain, ...}; chain has the hc_gate.chains_golden entry format
(h, src, attn / ffn = (pre, w, eps, comb, post, y), <blk>_checks = ([(label, addr, bits, kind)], [(...)], h_norm_in,
h_post_in)) plus h_in.  Deterministic (no timestamp): the same inputs give the same bytes.

    python3 tools/s81_ctrl/die_layer_chain.py --layer 14 --out <dir>/hc_chain_L14.pkl
"""
import argparse, hashlib, json, os, pickle, sys
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81_suhc'))
F = np.float32
CTX = 1048576
GOLD = Path(os.environ.get("OT_DSROM_1M_GOLD", "/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))
SCHEMA = "opentallas.s81-ctrl.die-layer-hc-chain.v1"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def same(a, b):
    a, b = np.asarray(a, F), np.asarray(b, F)
    return bool(a.shape == b.shape and np.array_equal(a.view(np.uint32), b.view(np.uint32)))


def load(path, layer):
    """The chain of `layer` ("L14") from a fixture this tool wrote."""
    d = pickle.loads(Path(path).read_bytes())
    assert d["schema"] == SCHEMA and d["layer"] == layer, (d.get("schema"), d.get("layer"), layer)
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--layer', type=int, default=14)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    import hc_gate as HG
    L = a.layer
    shard = GOLD / f"ctx{CTX}_L{L:02d}.npz"
    z = np.load(shard)
    ck = LC.Checkpoint()
    m, init_sha = LC.build_model(ck, engram=True)
    hist = json.loads((GOLD / f"golden_ctx{CTX}_0-39.json").read_text())["history"]
    h_in = z["h_in"].astype(F)
    checks = {}
    engram = L in m.engram.layer_ids
    h = h_in
    if engram:
        h = m.engram_layer(h_in.copy(), L, hist)
        checks["engram_equals_shard"] = same(h, z[f"L{L}.engram"])
    h0 = np.asarray(h, F).copy()
    ch = dict(h=h0, h_in=h_in.copy(), src=f"L{L}")
    eps = F(m.eps)
    pre = np.asarray(z["pre_in"], F)
    hb = h0
    for blk in ("attn", "ffn"):
        b_pre, b_post, b_comb = m.hc_mixes(hb, L, blk)
        w = np.asarray(m.lw(L, f"{blk}_norm.weight"), F).copy()
        y = np.asarray(z[f"L{L}.{blk}"], F)
        x = V.rmsnorm_fold(m.hc_pre(hb, pre), w, m.eps)
        hn = m.hc_post(y, hb, b_post, b_comb)
        comb, post = np.asarray(b_comb, F).reshape(4, 4).copy(), np.asarray(b_post, F).copy()
        xg = HG.g_norm(hb, pre, w, eps)
        hg = HG.g_post(hb, y, comb, post)
        checks[f"{blk}_norm_equals_shard"] = same(x, z[f"L{L}.{blk}_norm"])
        checks[f"{blk}_norm_hc_gate_equals_shard"] = same(xg, z[f"L{L}.{blk}_norm"])
        checks[f"{blk}_post_hc_gate_equals_model"] = same(hg, hn)
        ch[blk] = (pre.copy(), w, eps, comb, post, y.copy())
        ch[blk + "_checks"] = ([(f"L{L}.{blk}_norm (shard)", -1, HG.u32(z[f"L{L}.{blk}_norm"]).copy(), "write")],
                               [(f"h after L{L}.{blk} hc_post (golden model)", -1, HG.u32(hn).reshape(-1).copy(), "write")],
                               hb.copy(), hb.copy())
        pre, hb = np.asarray(b_pre, F).copy(), np.asarray(hn, F).copy()
    checks["h_out_equals_shard"] = same(hb, z["h_out"])
    checks["h_out_equals_block"] = same(hb, z[f"block{L}"])
    checks["pre_out_equals_shard"] = same(pre, z["pre_out"])
    ch["h_out"], ch["pre_out"] = hb, pre
    print(json.dumps(checks, indent=1))
    assert all(checks.values()), "L%d HC chain is not bit-exact against the shard: nothing written" % L
    fx = dict(schema=SCHEMA, layer=f"L{L}", context=CTX, engram=bool(engram), chain=ch, checks=checks,
              shard=shard.name, shard_sha256=sha(shard), checkpoint=str(LC.HF), golden_init_sha256=init_sha,
              arith=os.environ["HDC_V41_ARITH"],
              golden_sha256={p: sha(ROOT / p) for p in ("tools/hdc_golden_v41.py", "tools/hdc_golden.py")})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(pickle.dumps(fx, protocol=4))
    print(a.out, sha(a.out))


if __name__ == '__main__':
    main()
