#!/usr/bin/env python3
"""CPU-only HC nonlinear lowering and original-golden boundary oracle.

Exact software instructions, not GPU intrinsics/timing/eligibility. The dot is
the integrated full-F32 chunk8 prerequisite; no norm-after-matvec variant.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V
import w19_hc_simd_proof as D

F = np.float32


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Instructions:
    def __init__(self):
        self.trace = []

    def boundary(self, op, value):
        value = np.asarray(value, dtype=F)
        self.trace.append((op, value.copy()))
        return value

    def z(self, value):
        value = np.asarray(value, dtype=F)
        return np.where(value == 0, F(0), value).astype(F)

    def add(self, a, b):
        return self.boundary("add", self.z(np.asarray(a, dtype=F) + np.asarray(b, dtype=F)))

    def mul(self, a, b):
        return self.boundary("mul", self.z(np.asarray(a, dtype=F) * np.asarray(b, dtype=F)))

    def neg(self, a):
        b = np.asarray(a, dtype=F).view(np.uint32) ^ np.uint32(0x80000000)
        return self.boundary("neg", b.view(F))

    def div(self, a, b):
        with np.errstate(divide="ignore", invalid="ignore"):
            result = np.asarray(a, dtype=F) / np.asarray(b, dtype=F)
        return self.boundary("div", self.z(result))

    def rsqrt(self, v):
        v = self.boundary("rsqrt.input", v)
        y = (np.uint32(0x5F3759DF) - (v.view(np.uint32) >> np.uint32(1))).view(F)
        y = self.boundary("rsqrt.seed", y)
        half = self.mul(v, F(0.5))
        for _ in range(3):
            y = self.mul(y, self.add(F(1.5), self.neg(self.mul(half, self.mul(y, y)))))
        return self.boundary("rsqrt.output", y)

    def exp(self, x):
        x = self.boundary("exp.input", x)
        x = self.boundary("exp.clamped", np.clip(x, G.EXP_MIN, G.EXP_MAX).astype(F))
        t = self.mul(x, G.LOG2E)
        u = self.add(t, G.MAGIC)
        n = self.add(u, self.neg(G.MAGIC))
        r = self.add(self.add(x, self.neg(self.mul(n, G.LN2_HI))), self.neg(self.mul(n, G.LN2_LO)))
        p = np.full_like(r, G.EXP_POLY[0])
        for c in G.EXP_POLY[1:]:
            p = self.add(self.mul(p, r), c)
        b = p.view(np.uint32).astype(np.int64) + (n.astype(np.int64) << 23)
        return self.boundary("exp.output", b.astype(np.uint32).view(F))

    def sigmoid(self, x):
        return self.div(F(1), self.add(self.exp(self.neg(x)), F(1)))

    def seqsum(self, terms):
        acc = terms[0]  # golden short sums start at term0, not an invented +0
        for term in terms[1:]:
            acc = self.add(acc, term)
        return acc

    def csum(self, a):
        a = np.asarray(a, dtype=F).reshape(-1, 8)
        acc = np.zeros(a.shape[0], F)
        for j in range(8):
            acc = self.add(acc, a[:, j])
        pad = 1 << (len(acc) - 1).bit_length()
        acc = np.pad(acc, (0, pad - len(acc)))
        while len(acc) > 1:
            acc = self.add(acc[0::2], acc[1::2])
        return F(acc[0])


def validate_fixture(w, x, scale, base, cfg):
    D.validate(w, x.reshape(-1))
    if x.shape != (4, 5120) or scale.shape != (3,) or base.shape != (24,):
        raise ValueError("HC requires x[4,5120], scale[3], base[24]")
    if scale.dtype != F or base.dtype != F or not np.isfinite(scale).all() or not np.isfinite(base).all():
        raise ValueError("finite F32 scale/base required")
    if cfg["hc_mult"] != 4 or cfg["hc_sinkhorn_iters"] != 20 or not np.isfinite([cfg["rms_norm_eps"], cfg["hc_eps"]]).all() or cfg["rms_norm_eps"] <= 0 or cfg["hc_eps"] <= 0:
        raise ValueError("released four-copy twenty-iteration HC contract required")


def lower(w, x, scale, base, cfg, dot=None):
    validate_fixture(w, x, scale, base, cfg)
    I = Instructions()
    flat = x.reshape(-1)
    eps, heps = F(cfg["rms_norm_eps"]), F(cfg["hc_eps"])
    r = I.rsqrt(I.add(I.div(I.csum(I.mul(flat, flat)), F(flat.size)), eps))
    dot = D.reference(w, flat) if dot is None else dot
    if dot.shape != (24,) or dot.dtype != F or not np.isfinite(dot).all():
        raise ValueError("dot prerequisite must provide 24 finite F32 outputs")
    mixes = I.mul(I.boundary("dot", dot), r)
    pre = I.add(I.sigmoid(I.add(I.mul(mixes[:4], scale[0]), base[:4])), heps)
    post = I.mul(I.sigmoid(I.add(I.mul(mixes[4:8], scale[1]), base[4:8])), F(2))
    comb = I.add(I.mul(mixes[8:], scale[2]), base[8:]).reshape(4, 4)
    maximum = np.max(comb, axis=1, keepdims=True)
    e = I.exp(I.add(comb, I.neg(maximum)))
    rs = I.seqsum([e[:, k] for k in range(4)])
    comb = I.add(I.div(e, rs[:, None]), heps)
    I.boundary("sinkhorn.softmax_eps", comb)

    def cols(cm):
        cs = I.seqsum([cm[j, :] for j in range(4)])
        return I.boundary("sinkhorn.cols", I.div(cm, I.add(cs, heps)[None, :]))

    def rows(cm):
        rs = I.seqsum([cm[:, k] for k in range(4)])
        return I.boundary("sinkhorn.rows", I.div(cm, I.add(rs, heps)[:, None]))

    comb = cols(comb)
    for _ in range(19):
        comb = cols(rows(comb))
    return (pre, post, comb), I.trace


@contextmanager
def instrument_original(I, dot):
    """Temporary primitive logging; always restore golden globals and mode.

The original Model.hc_mixes body and original SFU bodies execute unchanged.
Dot substitution only consumes the independently validated integrated dot.
"""
    originals = {(m, n): getattr(m, n) for m in (G, V) for n in ("add", "mul", "neg", "exp", "rsqrt")}
    originals[(V, "div")] = V.div
    originals[(V, "matvec_c")] = V.matvec_c
    originals[(V, "seqsum")] = V.seqsum
    oldmode = V.ARITH
    def wrap(op, f):
        def call(*args, **kwargs):
            return I.boundary(op, f(*args, **kwargs))
        return call
    def special(op, f):
        def call(x):
            x = I.boundary(op + ".input", x)
            if op == "rsqrt":
                seed = (np.uint32(0x5F3759DF) - (x.view(np.uint32) >> np.uint32(1))).view(F)
                I.boundary("rsqrt.seed", seed)
            else:
                I.boundary("exp.clamped", np.clip(x, G.EXP_MIN, G.EXP_MAX).astype(F))
            return I.boundary(op + ".output", f(x))
        return call
    # Row/column semantic boundaries are observed at return from original local
    # funcs by Python tracing; no rewritten Sinkhorn body serves as oracle.
    import sys
    oldtrace = sys.gettrace()
    def observer(frame, event, arg):
        if event == "return" and frame.f_code.co_name in ("cols", "rows") and frame.f_code.co_filename == V.__file__:
            I.boundary("sinkhorn." + frame.f_code.co_name, arg)
        if event == "call" and frame.f_code.co_name == "cols" and frame.f_code.co_filename == V.__file__:
            if not any(n.startswith("sinkhorn.") for n, _ in I.trace):
                I.boundary("sinkhorn.softmax_eps", frame.f_locals["cm"])
        return observer
    try:
        for m in (G, V):
            for name in ("add", "mul", "neg"):
                setattr(m, name, wrap(name, originals[(m, name)]))
            for name in ("exp", "rsqrt"):
                setattr(m, name, special(name, originals[(m, name)]))
        V.div = wrap("div", originals[(V, "div")])
        V.matvec_c = lambda *a, **k: I.boundary("dot", dot)
        V.ARITH = "chunk8"
        sys.settrace(observer)
        yield
    finally:
        sys.settrace(oldtrace)
        V.ARITH = oldmode
        for (m, n), f in originals.items():
            setattr(m, n, f)


def oracle(w, x, scale, base, cfg, dot=None):
    validate_fixture(w, x, scale, base, cfg)
    dot = D.reference(w, x.reshape(-1)) if dot is None else dot
    I = Instructions()
    weights = {"fn": w, "scale": scale, "base": base}
    model = SimpleNamespace(hc=4, eps=F(cfg["rms_norm_eps"]), hc_eps=F(cfg["hc_eps"]), sinkhorn_iters=20,
                            lw=lambda L, name: weights[name.rsplit("_", 1)[-1]])
    with instrument_original(I, dot):
        out = V.Model.hc_mixes(model, x, 0, "attn")
    return out, I.trace


def compare(actual, expected):
    if len(actual) != len(expected):
        raise AssertionError(f"boundary count mismatch {len(actual)} vs {len(expected)}")
    for i, ((an, av), (en, ev)) in enumerate(zip(actual, expected)):
        if an != en or av.shape != ev.shape or not np.array_equal(av.view(np.uint32), ev.view(np.uint32)):
            raise AssertionError(f"boundary {i}: {an}{av.shape} vs {en}{ev.shape}")
    return len(actual)


def release_config(raw):
    cfg = raw["text_config"] if "text_config" in raw else raw
    if cfg["hidden_size"] != 5120 or cfg["hc_mult"] != 4:
        raise ValueError("released normative HC shape mismatch")
    return cfg


def fixtures(snapshot):
    from safetensors import safe_open
    cfg = release_config(json.loads((snapshot / "config.json").read_text()))
    idx = snapshot / "model.safetensors.index.json"
    mapping = json.loads(idx.read_text())["weight_map"]
    for prefix in ("layers.0.hc_attn_", "layers.39.hc_ffn_"):
        arrays, pins = {}, {}
        for part in ("fn", "scale", "base"):
            name = prefix + part
            shard = snapshot / mapping[name]
            with safe_open(str(shard), framework="np") as f:
                arrays[part] = f.get_tensor(name).copy()
            if arrays[part].dtype != F:
                raise ValueError("actual checkpoint HC coefficients must be F32")
            pins[name] = {"sha256": sha(arrays[part].tobytes()), "shape": list(arrays[part].shape), "dtype": "F32", "shard": str(shard.resolve())}
        for activation in ("seeded_normal_BF16", "all_positive_zero_BF16"):
            x = np.zeros((4, 5120), F)
            if activation.startswith("seeded"):
                x = G.to_bf16(np.random.default_rng(190033).normal(size=x.shape).astype(F))
            yield prefix + activation, arrays, x, cfg, {"snapshot": str(snapshot), "revision": snapshot.name,
                "config_sha256": sha((snapshot / "config.json").read_bytes()), "index_sha256": sha(idx.read_bytes()), "tensors": pins,
                "activation": activation, "disclosure": "synthetic BF16 activation, not actual model trajectory"}


def execute(out, snapshot):
    repo = Path(__file__).resolve().parents[1]
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip():
        raise RuntimeError("clean committed source required")
    out.mkdir(parents=True, exist_ok=False)
    dependency_path = "results/quality/w19_hc_simd_proof_20261001/proof.json"
    dependency_bytes = subprocess.check_output(["git", "show", "HEAD:" + dependency_path], cwd=repo)
    dependency = json.loads(dependency_bytes)
    if dependency["verdict"] != "PASS" or sha((repo / "tools/w19_hc_simd_proof.py").read_bytes()) != dependency["source_pins"]["tools/w19_hc_simd_proof.py"]:
        raise RuntimeError("integrated dot prerequisite source pin mismatch")
    prior_coefficients = {f["provenance"]["tensor"]: f["coefficient_sha256"] for f in dependency["fixtures"] if "tensor" in f["provenance"]}
    records = []
    for i, (name, a, x, cfg, provenance) in enumerate(fixtures(snapshot)):
        fn_name = next(n for n in provenance["tensors"] if n.endswith("_fn"))
        if prior_coefficients[fn_name] != sha(a["fn"].tobytes()):
            raise RuntimeError("checkpoint coefficient differs from integrated full-shape dot proof")
        dot = D.reference(a["fn"], x.reshape(-1))
        got, trace = lower(a["fn"], x, a["scale"], a["base"], cfg, dot)
        ref, expected = oracle(a["fn"], x, a["scale"], a["base"], cfg, dot)
        n = compare(trace, expected)
        for g, r in zip(got, ref):
            assert np.array_equal(g.view(np.uint32), r.view(np.uint32))
        np.savez_compressed(out / f"fixture_{i}.npz", **a, activation=x, dot=dot, pre=got[0], post=got[1], comb=got[2])
        boundaries = [{"ordinal": j, "instruction": op, "shape": list(v.shape), "sha256": sha(v.tobytes()),
                       "golden_sha256": sha(expected[j][1].tobytes()), "mismatched_bits": 0} for j, (op, v) in enumerate(trace)]
        (out / f"boundaries_{i}.json").write_text(json.dumps(boundaries, indent=2) + "\n")
        element_counts = Counter()
        for op, v in trace:
            element_counts[op] += v.size
        records.append({"name": name, "provenance": provenance, "boundary_count": n, "boundary_instruction_counts": dict(Counter(op for op, _ in trace)),
                        "boundary_F32_element_counts": dict(element_counts), "hc_mult": 4,
                        "norm_eps": cfg["rms_norm_eps"], "hc_eps": cfg["hc_eps"], "sinkhorn_iters": 20, "verdict": "PASS"})
    pins = ["tools/w19_hc_nonlinear_proof.py", "tests/test_w19_hc_nonlinear_proof.py", "tools/hdc_golden.py", "tools/hdc_golden_v41.py", "tools/w19_hc_simd_proof.py"]
    control = Instructions()
    rv = np.array([0.125, 0.3, 2, 10, 1e-20], F)
    ev = np.array([-100, -1.3, 0.125, 1.9, 100], F)
    with np.errstate(over="ignore"):
        mutations = {"native_rsqrt_differing_words": int(np.count_nonzero(control.rsqrt(rv).view(np.uint32) != (F(1) / np.sqrt(rv)).view(np.uint32))),
                     "native_exp_differing_words": int(np.count_nonzero(control.exp(ev).view(np.uint32) != np.exp(ev).view(np.uint32)))}
    if not all(mutations.values()):
        raise AssertionError("native SFU negative controls lack sensitivity")
    r = {"schema": "opentallas.w19.hc-nonlinear.cpu-proof.v1", "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
         "source_pins": {p: sha((repo / p).read_bytes()) for p in pins}, "numpy": np.__version__, "fixtures": records,
         "integrated_dot_prerequisite": {"path": dependency_path, "sha256": sha(dependency_bytes), "coefficient_identity_checked": True}, "negative_controls": mutations,
         "verdict": "PASS", "backend": "CPU NumPy binary32, explicitly separated operations, original-golden instrumentation",
         "oracle_mode": "chunk8", "scope": "full-shape HC mixes pre/post/comb only; no hc_pre/hc_post residual application, actual model trajectory or GPU qualification",
         "GPU_campaign_launched": False, "model_eligibility": "REFUSED_PENDING_GPU_LOWERING_AND_RESOURCES", "rate": None, "adoption": False,
         "QC_NAM": "existing full FAIL unchanged", "artifacts": {p.name: sha(p.read_bytes()) for p in sorted(out.iterdir())}}
    (out / "proof.json").write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps({"verdict": "PASS", "fixtures": len(records), "boundaries": sum(f["boundary_count"] for f in records), "proof": str(out / "proof.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    execute(args.out, args.snapshot)
