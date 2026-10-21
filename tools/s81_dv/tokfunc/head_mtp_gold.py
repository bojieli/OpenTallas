#!/usr/bin/env python3
"""TOK-FUNC-S81/HEADMTP (10-21): bench goldens for the LM-head producer legs, built from the committed S81 HEAD layer
fixture (dv_layer_fixtures.py --layer HEAD; w17 1M token, next token 21946; hdc_golden_v41 chunk8).

Writes into OUT:
  xfin/{x,w,cfg,ey}.mem   tb_s81dv_xfin16 inputs (format of results/rtl/hbm_norm_engine_view_20261006/gold):
                          x = head.hop (the L39 exit h, 4 x 5120 FP32 holding BF16), w = norm.weight (FP32),
                          cfg = {pre_out[0..3], 5120.0, norm_eps}, ey = head.norm.scale (5120 BF16 in FP32)
  beat/bNN/*.mem          tb_s81sl_beat leaf image for beat NN (format of tools/s81_slice/leaf_gold.py): block a = the head
                          hc_pre + RMSNorm (pre = pre_out, gains = norm.weight, rstd / partial / y / XB = HEAD fixture);
                          block f and both hc_post steps have no head op: they run the same head norm again on hn = h
                          (comb = I, post = 0, so hn = h bit for bit).  Only block a is graded as the head producer.
  gold.json               shas + the checks below.
Every value is asserted against the fixture: hc_pre == head.hc_pre, csum == head.norm.sumsq, rstd == head.norm.rsqrt,
y == head.norm.scale (bit for bit), else nothing is written.

    python3 tools/s81_dv/tokfunc/head_mtp_gold.py --head FIXTURE_HEAD_DIR --out DIR
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "tools/s81_suhc"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import hc_gate as HG          # noqa: E402
import hdc_golden_v41 as V    # noqa: E402

F = np.float32; D = 5120


def u(x):
    return np.asarray(x, F).view(np.uint32)


def w32(p, a):
    np.savetxt(p, np.asarray(a, np.uint32).reshape(-1), fmt="%08x")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--head", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    V.set_arith("chunk8")
    fx = a.head
    files = json.loads((fx / "files.json").read_text())
    for rel in ("ops/head.hop.bin", "ops/head.hc_pre.bin", "ops/head.norm.sumsq.bin", "ops/head.norm.rsqrt.bin",
                "ops/head.norm.scale.bin", "io/pre_in.bin", "weights/norm.bin"):
        if rel in files and sha(fx / rel) != files[rel]["sha256"]:
            raise SystemExit(f"fixture hash mismatch {rel}")
    cfgj = json.loads((ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json").read_text())
    eps = F(cfgj["norm_eps"] if "norm_eps" in cfgj else cfgj["model"]["norm_eps"])
    h = np.fromfile(fx / "ops/head.hop.bin", "<f4").reshape(4, D)
    pre = np.fromfile(fx / "io/pre_in.bin", "<f4")
    wb = np.fromfile(fx / "weights/norm.bin", "<u2")
    w = (wb.astype(np.uint32) << 16).view(F)
    xp_g = np.fromfile(fx / "ops/head.hc_pre.bin", "<f4")
    ss_g = np.fromfile(fx / "ops/head.norm.sumsq.bin", "<f4")[0]
    r_g = np.fromfile(fx / "ops/head.norm.rsqrt.bin", "<f4")[0]
    y_g = np.fromfile(fx / "ops/head.norm.scale.bin", "<f4")
    x = V.to_bf16(V.seqsum([V.mul(F(pre[k]), h[k]) for k in range(4)]))
    sq = V.mul(x, x)
    tot = V.csum(sq)
    r = V.rsqrt(V.add(V.div(F(tot), F(D)), eps))
    y = HG.g_norm(h, pre, w, eps)
    yr = V.to_bf16(V.mul(w, V.mul(x, F(r))))
    checks = dict(hc_pre_equals_fixture=bool(np.array_equal(u(x), u(xp_g))),
                  sumsq_equals_fixture=bool(u(tot) == u(ss_g)), rstd_equals_fixture=bool(u(r) == u(r_g)),
                  y_equals_fixture=bool(np.array_equal(u(y), u(y_g))), rstd_path_equals_g_norm=bool(np.array_equal(u(yr), u(y))),
                  h_is_bf16=bool(not np.any(u(h) & 0xFFFF)))
    if not all(checks.values()):
        raise SystemExit(f"HEAD gold does not reproduce the fixture: {checks}")
    out = a.out; (out / "xfin").mkdir(parents=True, exist_ok=True)
    w32(out / "xfin/x.mem", u(h)); w32(out / "xfin/w.mem", u(w))
    w32(out / "xfin/cfg.mem", u(list(pre) + [F(D), eps])); w32(out / "xfin/ey.mem", u(y_g))
    comb = np.eye(4, dtype=F); post = np.zeros(4, F)
    q = HG.g_quant(y)
    hn = HG.g_post(h, np.asarray(y, F), comb, post)
    assert np.array_equal(u(hn), u(h)), "identity hc_post must return h"
    for b in range(80):
        d = out / f"beat/b{b:02d}"; d.mkdir(parents=True, exist_ok=True)
        sl = slice(64 * b, 64 * b + 64)
        np.savetxt(d / "h0.mem", (u(h[:, sl]) >> 16).reshape(-1), fmt="%04x")
        bp = V.csum(sq[sl])
        for tag in ("a", "f"):
            w32(d / f"{tag}_pre.mem", u(pre)); w32(d / f"{tag}_w.mem", u(w[sl])); w32(d / f"{tag}_eps.mem", u([eps]))
            w32(d / f"{tag}_rstd.mem", u([r])); w32(d / f"{tag}_bp.mem", u([bp])); w32(d / f"{tag}_y.mem", u(y[sl]))
            qb = q[2 * b:2 * b + 2]
            (d / f"{tag}_q.mem").write_text("".join("%064x\n" % int.from_bytes(bytes(np.asarray(c, np.uint8)), "little") for e, c in qb))
            (d / f"{tag}_e.mem").write_text("".join("%03x\n" % (int(e) & 0x3FF) for e, c in qb))
            w32(d / f"{tag}_comb.mem", u(comb.reshape(-1))); w32(d / f"{tag}_post.mem", u(post))
            w32(d / f"{tag}_yp.mem", u(np.asarray(y, F)[sl]))
            np.savetxt(d / f"{tag}_hn.mem", (u(hn[:, sl]) >> 16).reshape(-1), fmt="%04x")
    rec = dict(schema="opentallas.tokfunc_s81.head_gold.v1", fixture=str(fx), fixture_files_json_sha256=sha(fx / "files.json"),
               eps=float(eps), pre=[float(t) for t in pre], rstd_bits=f"{int(u(r)):08x}", checks=checks,
               xfin_sha256={k: sha(out / f"xfin/{k}.mem") for k in ("x", "w", "cfg", "ey")},
               sources={p: sha(ROOT / p) for p in ("tools/s81_dv/tokfunc/head_mtp_gold.py", "tools/hdc_golden_v41.py",
                                                    "tools/s81_suhc/hc_gate.py")})
    (out / "gold.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("HEAD_GOLD OK", json.dumps(checks))


if __name__ == "__main__":
    main()
