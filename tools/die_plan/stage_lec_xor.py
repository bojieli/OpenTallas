#!/usr/bin/env python3
"""Stage the measured optional cp310 XOR SAT dependency from a pinned wheel.

Usage: stage_lec_xor.py WHEEL OUTDIR
Set OT_LEC_SOLVER=OUTDIR when launching LEC. No global Python installation.
"""
import argparse
import hashlib
from pathlib import Path
import zipfile

WHEEL = "pycryptosat-5.17.0-cp310-cp310-manylinux_2_34_x86_64.whl"
SHA256 = "15dff341a2b98368497f54f85326e0e8056684d73fbb5867998152fd7cf58746"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("wheel", type=Path)
    ap.add_argument("out", type=Path)
    args = ap.parse_args()
    digest = hashlib.sha256(args.wheel.read_bytes()).hexdigest()
    if args.wheel.name != WHEEL or digest != SHA256:
        ap.error("expected pinned %s SHA256 %s; received %s" % (WHEEL, SHA256, digest))
    args.out.mkdir(parents=True, exist_ok=True)
    root = args.out.resolve()
    with zipfile.ZipFile(args.wheel) as z:
        if any(not (root / n).resolve().is_relative_to(root) for n in z.namelist()):
            ap.error("wheel contains a path outside output directory")
        z.extractall(root)
    (root / "LEC_XOR_DEPENDENCY.txt").write_text(
        "%s\nsha256 %s\nABI cp310; pycryptosat 5.17.0; optional unchanged lec.py xor_sat backend\n" % (WHEEL, SHA256))
    print("OT_LEC_SOLVER=" + str(root))


if __name__ == "__main__":
    main()
