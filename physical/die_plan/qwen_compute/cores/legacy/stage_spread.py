#!/usr/bin/env python3
"""Stage a QC south-row prototype from an immutable existing kit/checkpoint."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from spread_south import configure


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source")
    ap.add_argument("out")
    ap.add_argument("--offset-um", type=float, default=8.64)
    ap.add_argument("--stride", type=int, default=4)
    a = ap.parse_args()
    src, out = Path(a.source).resolve(), Path(a.out).resolve()
    if out.exists():
        raise SystemExit("refuse to overwrite existing prototype")
    if json.loads((src/"face_guard.json").read_text()).get("verdict") != "PASS":
        raise SystemExit("source face_guard is not PASS")
    if "SDC_LINT PASS" not in (src/"sdc_lint.log").read_text():
        raise SystemExit("source sdc_lint is not PASS")
    base = next(src.glob("run/results/asap7/*/base"))
    out.mkdir(parents=True)
    subprocess.run(["rsync", "-aL", "--exclude=run", "--exclude=signoff", "--exclude=so",
                    str(src)+"/", str(out)+"/"], check=True)
    dst = out / base.relative_to(src)
    dst.mkdir(parents=True)
    for p in base.iterdir():
        if p.is_file() and (p.name.startswith(("1_", "2_")) or p.name == "clock_period.txt"):
            shutil.copy2(p, dst/p.name)
    if not (dst/"2_floorplan.odb").exists():
        raise SystemExit("source has no floorplan checkpoint; stop before prototype")
    for n in ("logs", "reports", "objects"):
        target = out/"run"/n/"asap7"/base.parent.name/"base"
        target.mkdir(parents=True)
        if n == "objects":
            shutil.copytree(src/"run"/n/"asap7"/base.parent.name/"base", target, dirs_exist_ok=True)
    manifest = configure(out, a.offset_um, a.stride)
    manifest.update(source=str(src), source_netlist_sha256=hashlib.sha256((base/"1_synth.v").read_bytes()).hexdigest(),
                    prototype="place plus ideal-clock GRT congestion only; no timing or signoff claim")
    (out/"SOUTH_SPREAD.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
