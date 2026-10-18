#!/usr/bin/env python3
"""S81-SLICE beat-leaf golden (one layer chain of the 1M token's real operands, su_cases pickle via hc_gate.chains_golden).

For beat b (global elements [64 b, 64 b + 64), slice b // 5, leaf b % 5) writes into OUT:
  h0.mem                 4 x 64 BF16 (copy-major) at the layer's entry
  {a,f}_pre.mem          hc_pre coefficients (4 FP32)           {a,f}_w.mem   64 gains          {a,f}_eps.mem
  {a,f}_rstd.mem         the golden rstd of the full 5,120 row   {a,f}_bp.mem  the beat partial (golden csum subtree)
  {a,f}_y.mem            64 normed y (FP32 holding BF16)         {a,f}_q.mem   2 x {codes 256 b} ; {a,f}_e.mem 2 x e
  {a,f}_comb.mem         comb[j][k] at 4 j + k (16)             {a,f}_post.mem 4      {a,f}_yp.mem 64 FP32 (hc_post y)
  {a,f}_hn.mem           4 x 64 BF16 after the block's hc_post (copy-major)
Chain: h0 -> attn norm / quant -> hc_post attn = h1 -> ffn norm / quant -> hc_post ffn = h2 (a_hn = h1, f_hn = h2).
    python3 tools/s81_slice/leaf_gold.py CASES.pkl BEAT OUT [L0|L2]
"""
import pickle
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "tools/s81_suhc"))
import hc_gate as HG
import hdc_golden_v41 as V

F = np.float32; D = 5120


def u(x):
    return np.asarray(x, F).view(np.uint32)


def w32(p, a):
    np.savetxt(p, np.asarray(a, np.uint32).reshape(-1), fmt="%08x")


def main():
    cases = pickle.load(open(sys.argv[1], "rb")); b = int(sys.argv[2]); out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    L = sys.argv[4] if len(sys.argv) > 4 else "L0"
    V.set_arith("chunk8")
    ch = [c for c in HG.chains_golden(cases) if c["src"] == L][0]
    sl = slice(64 * b, 64 * b + 64)
    h = np.asarray(ch["h"], F)
    np.savetxt(out / "h0.mem", (u(h[:, sl]) >> 16).reshape(-1), fmt="%04x")
    for tag, blk in (("a", "attn"), ("f", "ffn")):
        pre, w, eps, comb, post, yp = ch[blk]
        pre = np.asarray(pre, F); w = np.asarray(w, F); eps = F(eps)
        x = V.to_bf16(V.seqsum([V.mul(F(pre[k]), h[k]) for k in range(4)]))
        y = HG.g_norm(h, pre, w, eps)
        sq = V.mul(x, x)
        tot = V.csum(sq)
        r = V.rsqrt(V.add(V.div(F(tot), F(D)), F(eps)))
        yr = V.to_bf16(V.mul(w, V.mul(x, F(r))))
        assert np.array_equal(u(yr), u(y)), "rstd path does not reproduce g_norm"
        bp = V.csum(sq[sl])
        q = HG.g_quant(y)[2 * b:2 * b + 2]
        hn = HG.g_post(h, np.asarray(yp, F), np.asarray(comb, F), np.asarray(post, F))
        w32(out / f"{tag}_pre.mem", u(pre)); w32(out / f"{tag}_w.mem", u(w[sl])); w32(out / f"{tag}_eps.mem", u([eps]))
        w32(out / f"{tag}_rstd.mem", u([r])); w32(out / f"{tag}_bp.mem", u([bp])); w32(out / f"{tag}_y.mem", u(y[sl]))
        open(out / f"{tag}_q.mem", "w").write("".join("%064x\n" % int.from_bytes(bytes(np.asarray(c, np.uint8)), "little") for e, c in q))
        open(out / f"{tag}_e.mem", "w").write("".join("%03x\n" % (int(e) & 0x3FF) for e, c in q))
        w32(out / f"{tag}_comb.mem", u(np.asarray(comb, F).reshape(-1))); w32(out / f"{tag}_post.mem", u(post))
        w32(out / f"{tag}_yp.mem", u(np.asarray(yp, F)[sl]))
        np.savetxt(out / f"{tag}_hn.mem", (u(hn[:, sl]) >> 16).reshape(-1), fmt="%04x")
        h = hn
    print("LEAF_GOLD %s beat=%d slice=%d leaf=%d" % (L, b, b // 5, b % 5))


if __name__ == "__main__":
    main()
