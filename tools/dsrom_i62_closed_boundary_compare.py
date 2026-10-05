#!/usr/bin/env python3
"""One closed native I62 EXP/SUM boundary, using actual Sscaled/MAX inputs.

Uses the existing golden EXP (separate binary32 RNE steps, not libm) and chunk8
sum order. Refuses unfinished boundary files. Never runs/mutates the runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import numpy as np
from hdc_golden import add, exp, neg


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def csum(x):
    chunks = x.reshape(16, 80, 8)
    acc = np.zeros((16, 80), dtype=np.float32)
    for j in range(8):
        acc = add(acc, chunks[:, :, j])
    acc = np.pad(acc, ((0, 0), (0, 48)))
    while acc.shape[1] > 1:
        acc = add(acc[:, 0::2], acc[:, 1::2])
    return acc[:, 0].view(np.uint32)


def comparison(a, b, width):
    m = np.flatnonzero(a.ravel() != b.ravel())
    first = None
    if m.size:
        i = int(m[0])
        first = {"index": i, "head": i // width, "row": i % width,
                 "actual": f"{int(a.ravel()[i]):08x}", "golden": f"{int(b.ravel()[i]):08x}"}
    return {"words": int(a.size), "mismatches": int(m.size), "first": first}


def run(root, out):
    log = (root / "runtime.log").read_text()
    cycles = {}
    for name in ("Sscaled", "MAX", "EXP", "SUM"):
        m = re.search(rf"^BOUNDARY {name} cycle=(\d+)$", log, re.M)
        if not m:
            raise ValueError(f"closed source readback event missing: {name}")
        cycles[name] = int(m[1])
    files = {n: root / "captured" / (n + ".u32") for n in cycles}
    for n, p in files.items():
        if p.stat().st_size != (64 if n in ("MAX", "SUM") else 40960):
            raise ValueError(f"incomplete boundary extent: {n}")
    before = {n: sha(p) for n, p in files.items()}
    lit = root / "source/literals.hpp"
    line = next(x for x in lit.read_text().splitlines() if x.startswith("{2533,"))
    word = sum(int(s, 16) << (32 * i) for i, s in enumerate(re.findall(r"0x([0-9a-f]+)u", line)))
    fields = {"nout": (482, 21), "nin_dynamic": (530, 6), "m1": (966, 3),
              "m2": (969, 2), "qm": (971, 3), "ad": (974, 3), "sfu": (977, 3),
              "e1": (980, 3), "e2": (983, 2), "arnd": (962, 1), "rnd": (985, 1),
              "red": (1084, 2), "redwhole": (1087, 1), "redtree": (1697, 1),
              "redrnd": (1088, 1), "bbase": (668, 30), "bso": (698, 30), "bsi": (728, 30)}
    descriptor = {n: (word >> o) & ((1 << w) - 1) for n, (o, w) in fields.items()}
    expected = dict(nout=16, nin_dynamic=34, m1=0, m2=0, qm=0, ad=3, sfu=1,
                    e1=0, e2=0, arnd=0, rnd=0, red=1, redwhole=0, redtree=0,
                    redrnd=0, bbase=74176, bso=1, bsi=0)
    if descriptor != expected:
        raise ValueError("frozen I62 descriptor does not implement enrolled comparison")
    scaled = np.fromfile(files["Sscaled"], dtype="<u4").reshape(16, 640).view(np.float32)
    maximum = np.fromfile(files["MAX"], dtype="<u4").view(np.float32)
    actual_exp = np.fromfile(files["EXP"], dtype="<u4").reshape(16, 640)
    actual_sum = np.fromfile(files["SUM"], dtype="<u4")
    difference = add(scaled, neg(maximum[:, None]))
    golden_exp = exp(difference).astype(np.float32)
    golden_sum = csum(golden_exp)
    actual_exp_sum = csum(actual_exp.view(np.float32))
    checks = {"EXP": comparison(actual_exp, golden_exp.view(np.uint32), 640),
              "SUM_from_golden_EXP": comparison(actual_sum, golden_sum, 1),
              "SUM_from_actual_EXP": comparison(actual_sum, actual_exp_sum, 1)}
    if before != {n: sha(p) for n, p in files.items()}:
        raise ValueError("boundary bytes changed during comparison")
    out.mkdir(exist_ok=False)
    golden_exp.astype("<f4").tofile(out / "golden_EXP.u32")
    golden_sum.astype("<u4").tofile(out / "golden_SUM.u32")
    record = {"scope": "Closed native I62 EXP/SUM from actual Sscaled/MAX; no endpoint replay or original-run qualification",
              "capture_root": str(root), "boundary_cycles": cycles, "capture_sha256": before,
              "descriptor": descriptor, "literal_sha256": sha(lit),
              "tool_sha256": sha(Path(__file__)), "golden_sha256": sha(Path(__file__).with_name("hdc_golden.py")),
              "checks": checks, "original_full_run_qualified": False, "PV_qualified": False,
              "verdict": "PASS" if all(c["mismatches"] == 0 for c in checks.values()) else "FAIL"}
    (out / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return 0 if record["verdict"] == "PASS" else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    raise SystemExit(run(args.capture_root, args.out))
