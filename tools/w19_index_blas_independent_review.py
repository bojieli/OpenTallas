"""Independent directed input families; source reference is comparison only."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import deepseek_hbm_complete_index_blas as B
import deepseek_hbm_complete_index_consumer as C


def build():
    rng = np.random.default_rng(20261001)
    results = []
    for case in range(3):
        qraw = rng.uniform(-5, 5, (32, 128)).astype(np.float32)
        kraw = rng.uniform(-5, 5, (64, 128)).astype(np.float32)
        if case == 1:
            for h in range(0, 32, 3):
                qraw.view(np.uint32)[h, (h * 7) % 128] = [0x7fc12345, 0xffc23456, 0x7f800000, 0xff800000][h % 4]
            for k in range(0, 64, 5):
                kraw.view(np.uint32)[k, (k * 11) % 128] = [0x7fc34567, 0xff800000, 0x7f7fffff][k % 3]
        if case == 2:
            qraw *= np.float32(2 ** 100)
            kraw *= np.float32(2 ** 100)
        with np.errstate(invalid="ignore", over="ignore"):
            q = np.array([B.E.produce(row)[0] for row in qraw])
            keys = np.array([B.E.produce(row)[0] for row in kraw])
            weights = rng.uniform(-2, 2, 32).astype(np.float32)
            weights[::11] = 0
            got, _ = B.source_sized_scores(q, keys, weights, 5456)
            want = C.reference_scores(q, keys[np.arange(5456) % 64], weights, np.arange(5456))[:64]
        actual = got.astype(np.float64).view(np.uint64)
        expected = want.view(np.uint64)
        results.append({
            "case": case,
            "kind": ["all_finite", "source_produced_exceptional_with_finite_weights", "large_finite_products"][case],
            "raw_query_sha256": hashlib.sha256(qraw.tobytes()).hexdigest(),
            "raw_key_sha256": hashlib.sha256(kraw.tobytes()).hexdigest(),
            "weight_sha256": hashlib.sha256(weights.tobytes()).hexdigest(),
            "actual_F64bits": actual.tolist(), "expected_F64bits": expected.tolist(),
            "mismatch_indices": np.flatnonzero(actual != expected).tolist(),
        })
    return {"seed": 20261001, "original_batch": 5456, "queries": 32,
            "distinct_synthetic_keys": 64, "cases": results, "hardware_admission": False,
            "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "candidate_owner_commit": "922a6b673", "runtime": B.pinned_runtime(),
            "scope": "Directed independent software comparison only; no checkpoint, physical RF timing or full-domain proof."}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    if args.output.exists():
        raise ValueError("preserve prior verdicts")
    data = build()
    args.output.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
    if any(case["mismatch_indices"] for case in data["cases"]):
        raise SystemExit(1)
