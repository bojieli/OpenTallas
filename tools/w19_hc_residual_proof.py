#!/usr/bin/env python3
"""CPU-only exact HC residual application consuming archived mixes once.

No mixes/evaluator/GPU rerun. Synthetic identity block y=hc_pre output binds
the dependent edge; it does not model an attention/FFN block or token trajectory.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V

F = np.float32
PRODUCER = "results/quality/w19_hc_nonlinear_proof_20261001"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def array_sha(a):
    return sha(np.asarray(a).tobytes())


class Instructions:
    def __init__(self):
        self.trace = []

    def record(self, op, v):
        v = np.asarray(v, F)
        self.trace.append((op, v.copy()))
        return v

    def z(self, v):
        v = np.asarray(v, F)
        return np.where(v == 0, F(0), v).astype(F)

    def mul(self, a, b):
        return self.record("mul", self.z(np.asarray(a, F) * np.asarray(b, F)))

    def add(self, a, b):
        return self.record("add", self.z(np.asarray(a, F) + np.asarray(b, F)))

    def bf16(self, v):
        b = np.asarray(v, F).view(np.uint32).astype(np.uint64)
        rounded = ((b + np.uint64(0x7FFF) + ((b >> 16) & 1)) >> 16) << 16
        return self.record("bf16", rounded.astype(np.uint32).view(F))

    def seqsum(self, values):
        acc = values[0]
        for v in values[1:]:
            acc = self.add(acc, v)
        return acc


def validate(res, pre, post, comb):
    for a, shape in [(res, (4, 5120)), (pre, (4,)), (post, (4,)), (comb, (4, 4))]:
        if a.shape != shape or a.dtype != F or not np.isfinite(a).all():
            raise ValueError("finite normative F32 containers required")
    if not np.array_equal(res.view(np.uint32), G.to_bf16(res).view(np.uint32)):
        raise ValueError("residual must already be BF16-valued")


def lower_pre(res, pre):
    I = Instructions()
    products = [I.mul(pre[j], res[j]) for j in range(4)]
    out = I.bf16(I.seqsum(products))
    return out, I.trace


def lower_post(y, res, post, comb):
    I = Instructions()
    if y.shape != (5120,) or y.dtype != F or not np.isfinite(y).all() or not np.array_equal(y.view(np.uint32), G.to_bf16(y).view(np.uint32)):
        raise ValueError("block result must be finite BF16-valued y[5120]")
    mix = [I.seqsum([I.mul(comb[j, k], res[j]) for j in range(4)]) for k in range(4)]
    values = [I.add(I.mul(post[k], y), mix[k]) for k in range(4)]
    return I.bf16(np.stack(values)), I.trace


@contextmanager
def instrument(I):
    names = ("mul", "add", "to_bf16")
    saved = {n: getattr(V, n) for n in names}
    def wrap(n, f):
        def call(*a):
            return I.record("bf16" if n == "to_bf16" else n, f(*a))
        return call
    try:
        for n in names:
            setattr(V, n, wrap(n, saved[n]))
        yield
    finally:
        for n, f in saved.items():
            setattr(V, n, f)


def oracle(res, pre, y, post, comb):
    model = SimpleNamespace(hc=4)
    a, b = Instructions(), Instructions()
    with instrument(a):
        p = V.Model.hc_pre(model, res, pre)
    with instrument(b):
        q = V.Model.hc_post(model, y, res, post, comb)
    return p, q, a.trace, b.trace


def compare(a, b):
    if len(a) != len(b):
        raise AssertionError("boundary count mismatch")
    for i, ((op, x), (name, y)) in enumerate(zip(a, b)):
        if op != name or x.shape != y.shape or not np.array_equal(x.view(np.uint32), y.view(np.uint32)):
            raise AssertionError(f"boundary {i} mismatch: {op} vs {name}")
    return len(a)


@dataclass(frozen=True)
class Carry:
    res: np.ndarray
    pre: np.ndarray
    post: np.ndarray
    comb: np.ndarray
    manifest: dict
    manifest_sha256: str


def manifest_sha(m):
    return sha(json.dumps(m, sort_keys=True, separators=(",", ":")).encode())


def bind(res, pre, post, comb, producer):
    arrays = {n: a.copy() for n, a in zip(("res", "pre", "post", "comb"), (res, pre, post, comb))}
    validate(**arrays)
    for a in arrays.values():
        a.flags.writeable = False
    manifest = {"schema": "opentallas.w19.hc-residual.carry.v1", "producer": producer,
                "buffers": {n: array_sha(a) for n, a in arrays.items()},
                "edge": "original res retained through pre and synthetic identity block until all post outputs complete"}
    return Carry(**arrays, manifest=manifest, manifest_sha256=manifest_sha(manifest))


def check_carry(c):
    if manifest_sha(c.manifest) != c.manifest_sha256:
        raise ValueError("dependent carry provenance changed")
    validate(c.res, c.pre, c.post, c.comb)
    for n in ("res", "pre", "post", "comb"):
        if array_sha(getattr(c, n)) != c.manifest["buffers"][n]:
            raise ValueError(f"dependent carry changed: {n}")


def consume(c):
    check_carry(c)
    pre, a = lower_pre(c.res, c.pre)
    y = pre.copy()  # explicitly synthetic identity block, not deployed attention
    post, b = lower_post(y, c.res, c.post, c.comb)
    check_carry(c)  # no early overwrite of any original residual/broadcast
    return pre, y, post, a, b


def git_blob(repo, path):
    return subprocess.check_output(["git", "show", "HEAD:" + path], cwd=repo)


def producers(repo):
    raw = git_blob(repo, PRODUCER + "/proof.json")
    proof = json.loads(raw)
    if proof["verdict"] != "PASS" or proof["GPU_campaign_launched"]:
        raise ValueError("CPU mixes prerequisite must be terminal PASS")
    for n in ("tools/hdc_golden.py", "tools/hdc_golden_v41.py"):
        if sha((repo / n).read_bytes()) != proof["source_pins"][n]:
            raise ValueError("golden source changed since producer proof")
    blobs = {}
    for name, h in proof["artifacts"].items():
        blobs[name] = git_blob(repo, PRODUCER + "/" + name)
        if sha(blobs[name]) != h:
            raise ValueError("producer artifact hash mismatch")
    for i, f in enumerate(proof["fixtures"]):
        name = f"fixture_{i}.npz"
        with np.load(io.BytesIO(blobs[name]), allow_pickle=False) as a:
            producer = {"proof_path": PRODUCER + "/proof.json", "proof_sha256": sha(raw),
                        "source_commit": proof["source_commit"], "fixture": i, "fixture_name": f["name"],
                        "fixture_path": PRODUCER + "/" + name, "fixture_sha256": sha(blobs[name]),
                        "checkpoint": f["provenance"], "disclosure": "consume existing mixes output; no mixes execution or deployed block trajectory"}
            yield f["name"], bind(a["activation"], a["pre"], a["post"], a["comb"], producer)


def controls():
    x = np.ones((4, 5120), F)
    zero = np.zeros(4, F)
    yield "sequential4_tree_witness", bind(x, np.array([2**25, 1, -2**25, 1], F), zero, np.zeros((4, 4), F), {"origin": "synthetic control"})
    # Full F32 coefficient and BF16 residual product makes FMA differ from
    # separately rounded product after cancellation in hc_pre.
    x = np.zeros((4, 5120), F)
    x[0], x[1] = 1, F(1 - 2**-8)
    a = F(1 + 2**-23)
    p = np.array([-G.mul(a, x[1, 0]), a, 0, 0], F)
    yield "separate_product_witness", bind(x, p, zero, np.zeros((4, 4), F), {"origin": "synthetic control"})
    x = np.full((4, 5120), -0.0, F)
    yield "canonical_zero", bind(x, np.ones(4, F), np.ones(4, F), np.ones((4, 4), F), {"origin": "synthetic control"})
    x = np.ones((4, 5120), F)
    # Ties to even are observable at the final BF16 edge, not at coefficient input.
    p = np.array([0x3F808000, 0, 0, 0], np.uint32).view(F)
    yield "BF16_even_tie", bind(x, p, zero, np.zeros((4, 4), F), {"origin": "synthetic control"})
    p = np.array([0x3F818000, 0, 0, 0], np.uint32).view(F)
    yield "BF16_odd_tie", bind(x, p, zero, np.zeros((4, 4), F), {"origin": "synthetic control"})
    x = np.repeat(np.array([1, 2, 4, 8], F)[:, None], 5120, axis=1)
    yield "asymmetric_comb_index_witness", bind(x, np.array([1, 0, 0, 0], F), np.ones(4, F), np.arange(16, dtype=F).reshape(4, 4) / F(16), {"origin": "synthetic control"})


def execute(out):
    repo = Path(__file__).resolve().parents[1]
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip():
        raise ValueError("clean committed source required")
    out.mkdir(parents=True, exist_ok=False)
    records = []
    for i, (name, c) in enumerate(list(producers(repo)) + list(controls())):
        pre, y, post, a, b = consume(c)
        rp, rq, ra, rb = oracle(c.res, c.pre, y, c.post, c.comb)
        n = compare(a, ra) + compare(b, rb)
        assert np.array_equal(pre.view(np.uint32), rp.view(np.uint32))
        assert np.array_equal(post.view(np.uint32), rq.view(np.uint32))
        np.savez_compressed(out / f"fixture_{i}.npz", res=c.res, pre_coeff=c.pre, post_coeff=c.post, comb=c.comb, pre_output=pre, y=y, post_output=post)
        boundaries = [{"ordinal": j, "instruction": op, "shape": list(v.shape), "sha256": array_sha(v), "golden_sha256": array_sha((ra + rb)[j][1]), "mismatched_bits": 0} for j, (op, v) in enumerate(a + b)]
        (out / f"boundaries_{i}.json").write_text(json.dumps(boundaries, indent=2) + "\n")
        counts = Counter(); elements = Counter()
        for op, v in a + b:
            counts[op] += 1; elements[op] += v.size
        edge = {"source_pre_output_sha256": array_sha(pre), "block_result_y_sha256": array_sha(y), "synthetic_block": "identity; y=pre_output; no attention/FFN execution", "original_res_before_sha256": c.manifest["buffers"]["res"], "original_res_after_sha256": array_sha(c.res), "next_residual_output_sha256": array_sha(post)}
        wrong_post, _ = lower_post(y, c.res, c.post, c.comb.T.copy())
        rounded_pre, _ = lower_pre(c.res, G.to_bf16(c.pre))
        records.append({"name": name, "carry_manifest": c.manifest, "carry_manifest_sha256": c.manifest_sha256, "dependent_edge": edge, "boundaries": n, "instruction_counts": dict(counts), "F32_element_counts": dict(elements), "negative_controls": {"transpose_comb_differing_BF16_words": int(np.count_nonzero(wrong_post.view(np.uint32) != post.view(np.uint32))), "early_BF16_pre_coefficient_differing_words": int(np.count_nonzero(rounded_pre.view(np.uint32) != pre.view(np.uint32)))}, "verdict": "PASS"})
    pins = ["tools/w19_hc_residual_proof.py", "tests/test_w19_hc_residual_proof.py", "tools/hdc_golden.py", "tools/hdc_golden_v41.py"]
    if not any(f["negative_controls"]["transpose_comb_differing_BF16_words"] for f in records) or not any(f["negative_controls"]["early_BF16_pre_coefficient_differing_words"] for f in records):
        raise AssertionError("residual negative controls lack sensitivity")
    proof = {"schema": "opentallas.w19.hc-residual.cpu-proof.v1", "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(), "source_pins": {p: sha((repo / p).read_bytes()) for p in pins}, "numpy": np.__version__, "fixtures": records, "verdict": "PASS", "backend": "CPU only", "normative_shape": [4, 5120], "mixes_rerun": False, "GPU_campaign_launched": False, "model_eligibility": "REFUSED_PENDING_GPU_LOWERING_AND_RESOURCES", "rate": None, "adoption": False, "QC_NAM": "unchanged full FAIL", "artifacts": {p.name: sha(p.read_bytes()) for p in sorted(out.iterdir())}}
    (out / "proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"verdict": "PASS", "fixtures": len(records), "boundaries": sum(r["boundaries"] for r in records), "proof": str(out / "proof.json")}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    execute(p.parse_args().out)
