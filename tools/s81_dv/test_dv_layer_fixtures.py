#!/usr/bin/env python3
"""Pure-python tests of tools/s81_dv/dv_layer_fixtures.py (no checkpoint): the op-boundary splits reproduce the golden
expressions bit for bit, the exact FP8 packer keeps signed zero, the recorder refuses a duplicate op, the writer is
deterministic and --verify catches a changed file, and every committed manifest is well formed.

    python3 tools/s81_dv/test_dv_layer_fixtures.py
"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/s81_dv"))
import hdc_golden_v41 as V  # noqa: E402
import dv_layer_fixtures as X  # noqa: E402

F = np.float32
MAN = ROOT / "results/rtl/s81_layer_tput_1018/fixtures"


def t_rms_parts():
    rng = np.random.default_rng(1)
    x = V.to_bf16(rng.standard_normal(512).astype(F))
    w = V.to_bf16(rng.standard_normal(512).astype(F))
    r = X.Rec()
    y = X.rms_parts(V, x, w, F(1e-20), r, "attn.norm")
    assert X.same(y, V.rmsnorm_bf16(x, w, F(1e-20)))
    assert list(r.v) == ["attn.norm.sumsq", "attn.norm.rsqrt", "attn.norm.scale"]


def t_rec_dup():
    r = X.Rec()
    r("a", 1)
    try:
        r("a", 2)
    except AssertionError:
        return
    raise AssertionError("duplicate op accepted")


def t_attend():
    """attend() recorded op by op == Model.attend on a small model (2 heads, hd 64, 2 groups x 16)."""
    rng = np.random.default_rng(2)
    heads, hd, groups, o_rank, T = 2, 64, 2, 16, 9
    W = {"attn.attn_sink": rng.standard_normal(heads).astype(F),
         "attn.wo_a.weight": V.to_bf16(rng.standard_normal((groups * o_rank, heads * hd // groups)).astype(F))}
    # wo_b: an FP8 Q8 matrix [dim 64, groups * o_rank 16]
    q8 = V.Q8(np.asarray(rng.integers(-8, 9, size=(64, groups * o_rank)), np.float64),
              np.zeros((64, 1), np.int64))
    W["attn.wo_b.weight"] = q8
    m = types.SimpleNamespace(heads=heads, hd=hd, groups=groups, o_rank=o_rank, attn_scale=F(hd ** -0.5))
    m.lw = lambda L, n: W[n]
    m.attend = lambda L, q, kvm, cs, blocks=None: V.Model.attend(m, L, q, kvm, cs, blocks)
    freqs = V.rope_freqs(64, 0, 10000, 16, 32, 1)
    cs = V.rope_cs(freqs, 1234)
    q = V.to_bf16(rng.standard_normal((heads, hd)).astype(F))
    kvm = V.qdq_fp8(rng.standard_normal(T * hd).astype(F)).reshape(T, hd)
    r = X.Rec()
    y = X.attend(V, m, 0, q, kvm, cs, r)      # asserts == Model.attend inside
    for k in ("attn.scores", "attn.max", "attn.exp", "attn.pv", "attn.den", "attn.sink", "attn.normalize",
              "attn.wo_a", "attn.z_quant", "attn.wo_b", "attn.out_allreduce"):
        assert k in r.v, k
    assert y.shape == (64,)


def t_pack_fp8_signed_zero():
    import rtl_v41_fullshape_layer_campaign as LC
    rng = np.random.default_rng(3)
    rows = V.qdq_fp8(rng.standard_normal(4 * 64).astype(F)).reshape(4, 64)
    rows[1, 5] = F(-0.0)
    rows[2, 7] = F(0.0)
    c, e = X.pack_fp8_exact(V, LC, rows)
    assert c[1, 5] == 0x80 and c[2, 7] == 0x00
    try:
        LC.pack_fp8_ue8m0(rows)
        print("  (campaign packer accepted -0 on this draw)")
    except AssertionError:
        pass


def t_writer_verify():
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        for d in (d1, d2):
            o = X.Out(Path(d))
            o.put("ops/a.bin", np.arange(5, dtype=F))
            o.put("io/b.bin", np.ones((2, 3), F))
            o.manifest()
        assert (Path(d1) / "manifest.sha256").read_text() == (Path(d2) / "manifest.sha256").read_text()
        man = Path(d1) / "m.json"
        man.write_text(json.dumps({"files": {k: v["sha256"] for k, v in o.files.items()}}))
        assert X.main(["--verify", d2, "--manifest", str(man)]) == 0
        (Path(d2) / "ops/a.bin").write_bytes(b"x")
        assert X.main(["--verify", d2, "--manifest", str(man)]) == 1


def t_committed_manifests():
    need = {"L0", "L2", "L14", "L20", "HEAD"}
    have = {p.name.split(".")[0] for p in MAN.glob("*.sha256.json")}
    assert need <= have, need - have
    for p in MAN.glob("*.sha256.json"):
        d = json.loads(p.read_text())
        assert d["schema"] == X.SCHEMA + ".manifest", p
        assert all(d["checks"].values()), p
        assert d["files"] and all(len(h) == 64 for h in d["files"].values()), p
        assert set(d["op_order"]) == set(d["ops"]), p
        assert "dv_layer_fixtures.py" in d["command"], p


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("t_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"ALL {len(tests)} PASS")


if __name__ == "__main__":
    main()
