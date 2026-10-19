#!/usr/bin/env python3
"""LAYERBENCH-HBM (10-18): verify a Qwen D4G8 fixture dir (qwen_d4g_proof.py --dump) against its COMMITTED manifest.

Every file in manifest["files"] must exist with the recorded byte count and sha256 (sha256 of the raw bytes = of the
array, as write_fixture computes it); every expected.npz array must match manifest["expected"] (n, sha256).  Extra
files in the dir are listed (not an error).  Exit 0 = byte-identical fixture.
    verify_fixtures.py --dir FIX/L0 --manifest results/rtl/hbm_qwen_layer_tput_1018/fixtures/manifest_L0.json
"""
import argparse, hashlib, json, sys
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    a = ap.parse_args()
    man = json.loads(a.manifest.read_text())
    bad, nf = [], 0
    for name, e in man["files"].items():
        p = a.dir / name
        if not p.exists():
            bad.append(f"MISSING {name}"); continue
        h = hashlib.sha256()
        with p.open("rb") as f:
            for blk in iter(lambda: f.read(1 << 24), b""):
                h.update(blk)
        nf += 1
        if p.stat().st_size != e["bytes"] or h.hexdigest() != e["sha256"]:
            bad.append(f"DIFF {name} bytes {p.stat().st_size}/{e['bytes']} sha {h.hexdigest()[:16]}/{e['sha256'][:16]}")
    exp = np.load(a.dir / "expected.npz")
    ne = 0
    for k, e in man["expected"].items():
        if k not in exp.files:
            bad.append(f"MISSING expected[{k}]"); continue
        v = np.ascontiguousarray(exp[k]); ne += 1
        if int(v.size) != e["n"] or hashlib.sha256(v.tobytes()).hexdigest() != e["sha256"]:
            bad.append(f"DIFF expected[{k}]")
    extra = sorted({p.name for p in a.dir.iterdir()} - set(man["files"]) - {"expected.npz", "manifest.json"})
    for b in bad:
        print(b)
    print(f"FIXTURE_VERIFY {'PASS' if not bad else 'FAIL'} dir={a.dir} files={nf}/{len(man['files'])} "
          f"expected={ne}/{len(man['expected'])} mismatches={len(bad)} extra={extra}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
