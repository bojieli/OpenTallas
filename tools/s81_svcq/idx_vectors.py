#!/usr/bin/env python3
"""CLAUDE s81-svcq-1011 [svcq-idx]: golden vectors for the svc slab index reader gate (tb_s81_svcq_idx).

One select quarter (stack ST) of a pooled-index scan of N keys in the W11 quarter-per-stack ring layout
(RSB 64, RTAIL 32: C = 65,568 slots, UBLK 1,090 blocks a user a stack).  Query and keys are golden-quantised
(qdq_fp4_e8m0) normal vectors, head weights from the golden's weight line, keep = all (a full-scan layer); the
expected BF16 scores and fault flags are tools/hdc_golden_v41.py Model.indexer arithmetic under chunk8 (via
tools/rtl_hdc_v41x_idx_campaign.finish, the generator of the exact score-slice gates tools/rtl_w11_idx_array.py).
Writes per case: cfg.hex (32-bit: N, KB, user, k, ST, qstart, L, skip), q.hex (64 IDX_Q payload words), keys.hex
(L x 544 b, position order), exp.hex (L x {fault, BF16}).
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_w11_idx_array as A  # noqa: E402  (sets chunk8)
C = A.C
RSB, RTAIL = 64, 32
CAP = RSB * 1024 + RTAIL
# name: (N, ST, user, k)
CASES = {
    "q3_skip8_partial": (4013, 3, 1, 512),     # skip 952 (8 mod 16), partial last beat
    "q2_tiny": (46, 2, 1, 512),                # one dropped beat, partial
    "q1_empty": (20, 1, 1, 512),               # empty quarter
    "q3_1m_wrap": (262144, 3, 1, 512),         # 1M die slice, quarter 3: ring wrap (two segments)
    "q0_1m": (262144, 0, 1, 512),              # 1M die slice, quarter 0: one segment, full quarter
}


def words(fields):
    return int(C.hexline(fields), 16)


def make(out: Path, name, n, st, user, k, seed):
    out.mkdir(parents=True, exist_ok=True)
    qs = (n >> 5) << 3
    q0 = st * qs
    L = qs if st < 3 else n - 3 * qs
    h = q0 % CAP
    skip = h % 1024
    rng = np.random.default_rng(seed)
    t = A.normal_token(rng, max(L, 1), keep_p=1.0)
    qw = []
    for hh in range(A.IH):
        qw.append(words([(c, 4) for c in t["qc"][hh]]))
        qw.append(words([(u, 8) for u in t["qu"][hh]] + [(int(A.G.bits(t["w"][hh])) >> 16, 16)]))
    keys = [words([(c, 4) for c in t["kc"][i]] + [(u, 8) for u in t["ku"][i]]) for i in range(L)]
    exp = [(int(t["fault"][i]) << 16) | int(t["exp"][i]) for i in range(L)]
    (out / "q.hex").write_text("".join(f"{w:0128x}\n" for w in qw))
    (out / "keys.hex").write_text("".join(f"{w:0136x}\n" for w in keys) or "0\n")
    (out / "exp.hex").write_text("".join(f"{w:05x}\n" for w in exp) or "0\n")
    cfg = [n, 0, user, k, st, q0, L, skip]
    (out / "cfg.hex").write_text("".join(f"{w:08x}\n" for w in cfg + [0] * (16 - len(cfg))))
    return dict(name=name, N=n, ST=st, user=user, k=k, qstart=q0, L=L, ring_head=h, skip=skip,
                wraps=h + L > CAP, faults=int(sum(t["fault"][:L])), seed=seed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cases", default="")
    a = ap.parse_args()
    man = []
    for i, (nm, (n, st, u, k)) in enumerate(CASES.items()):
        if a.cases and nm not in a.cases.split(","):
            continue
        man.append(make(a.out / nm, nm, n, st, u, k, 20261011 + i))
        print(json.dumps(man[-1]), flush=True)
    (a.out / "manifest.json").write_text(json.dumps(dict(cases=man), indent=1) + "\n")


if __name__ == "__main__":
    main()
