#!/usr/bin/env python3
"""hgi-takeover 2026-10-09: vectors for IDX.MERGE (ot_hgi_idx_merge, proposed G20).

Each case: G runs of n {value, id} pairs, every run sorted by the merge key; the expected output is the first k of the
merged order, computed exactly as hgi_sim ds_native.topk_merge (np.lexsort((ids, -float64(values)))) for key 0, and by
id for key 1.  Values include ties across runs, -0 / +0, NaN, +-inf.  Case 'unsorted' breaks one run: must fault.
  hgi_idx_merge_vectors.py OUTDIR  -> OUTDIR/cases.txt (G n k key fault nexp per line) + case_<c>.{v,i,o,r}.mem
"""
import sys
from pathlib import Path
import numpy as np


def keyorder(v, i, key):
    if key == 1:
        return np.argsort(i, kind="stable")
    vv = v.view(np.float32).astype(np.float64)
    return np.lexsort((i, -vv))          # NaN sorts last (as the golden)


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261009)
    pool = np.array([5.0, 5.0, 2.5, 1.0, 0.0, -0.0, -1.0, np.inf, -np.inf, np.nan, 3.25, 7.0], dtype=np.float32)
    cases = []
    specs = [(96, 512, 512, 0), (96, 8, 512, 0), (4, 512, 512, 0), (8, 64, 100, 0), (1, 300, 300, 0), (96, 6, 512, 1),
             (128, 4, 600, 0), (3, 5, 20, 0), (2, 16, 7, 0), (96, 512, 512, 0)]
    for c, (G, n, k, key) in enumerate(specs):
        if c == len(specs) - 1:
            vals = rng.standard_normal((G, n)).astype(np.float32)       # realistic DS-like case, no special values
        else:
            vals = rng.choice(pool, size=(G, n)) if c % 2 == 0 else \
                np.where(rng.random((G, n)) < 0.3, rng.choice(pool, size=(G, n)), rng.standard_normal((G, n))).astype(np.float32)
        ids = rng.permutation(1 << 20)[:G * n].reshape(G, n).astype(np.uint32)
        V = vals.view(np.uint32).copy(); I = ids.copy()
        for g in range(G):                     # sort each run by the key
            o = keyorder(V[g], I[g], key)
            V[g], I[g] = V[g][o], I[g][o]
        fault = 0
        if c == 7:                             # break run 1: an unsorted run must fault
            V[1][[0, 2]] = V[1][[2, 0]]; I[1][[0, 2]] = I[1][[2, 0]]
            o = keyorder(V[1], I[1], key)
            if not np.array_equal(o, np.arange(n)):
                fault = 1
        fv, fi = V.reshape(-1), I.reshape(-1)
        o = keyorder(fv, fi, key)[:k]
        np.savetxt(out / f"case_{c}.v.mem", V.reshape(-1), fmt="%08x")
        np.savetxt(out / f"case_{c}.i.mem", I.reshape(-1), fmt="%08x")
        np.savetxt(out / f"case_{c}.o.mem", fi[o], fmt="%08x")
        np.savetxt(out / f"case_{c}.r.mem", fv[o], fmt="%08x")
        cases.append(f"{G} {n} {k} {key} {fault} {len(o)}")
    (out / "cases.txt").write_text(f"{len(cases)}\n" + "\n".join(cases) + "\n")
    print(cases)


if __name__ == "__main__":
    main()
