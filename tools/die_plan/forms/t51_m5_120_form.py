#!/usr/bin/env python3
"""Create a private T51 physical form from exact kit inputs and synth checkpoint.

Never modifies the source, overwrites a destination, or copies failed physical
verdicts. All-signal M5-M6 is intentional; it is not per-net layer assignment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


SKIP_DIRS = {"run", "signoff", "views", "render", "__pycache__"}
SKIP_FILES = {"image.txt", "PROVENANCE.json", ".ot-run-spill-copy"}


def ignored(directory, names):
    return [n for n in names if n in SKIP_DIRS or n in SKIP_FILES
            or n.startswith(("sta_", "postcts_gate_", "insertion_band", ".kwrs_done."))
            or n.endswith((".log", ".log.previous"))]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("destination", type=Path)
    ap.add_argument("--profile", type=Path, default=Path(__file__).with_name("t51_m5_120_profile.tcl"))
    args = ap.parse_args()
    src, dst = args.source.resolve(strict=True), args.destination.absolute()
    if dst.exists():
        raise SystemExit(f"destination exists; refusing overwrite: {dst}")
    checkpoints = list((src / "run/results/asap7").glob("*/base/1_synth.odb"))
    if len(checkpoints) != 1:
        raise SystemExit(f"expected one exact synth checkpoint, found {len(checkpoints)}")
    if any(p.is_symlink() for p in src.rglob("*") if "run" not in p.relative_to(src).parts):
        raise SystemExit("source input has symlinks; inspect dependencies before copying")
    config = (src / "config.mk").read_text()
    if "s81" not in config or "t51" not in config:
        raise SystemExit("source config does not identify T51")
    shutil.copytree(src, dst, ignore=ignored)
    base = checkpoints[0].parent
    out = dst / base.relative_to(src)
    out.mkdir(parents=True)
    copied = []
    for p in sorted(base.glob("1_*")):
        if p.is_file():
            shutil.copy2(p, out / p.name)
            copied.append({"path": str(p.relative_to(src)), "bytes": p.stat().st_size})
    shutil.copy2(args.profile, dst / "t51_m5_120_profile.tcl")
    additions = ["\n# Private physical form; same RTL/pin cycles as baseline.",
                 "override export MIN_ROUTING_LAYER = M5",
                 "override export MAX_ROUTING_LAYER = M6"]
    for key in ("PRE_GLOBAL_PLACE_TCL", "PRE_RESIZE_TCL", "PRE_GLOBAL_ROUTE_TCL"):
        values = re.findall(r"^(?:override\s+)?export\s+" + key + r"\s*[?:+]?=\s*(.+)$", config, re.M)
        original = values[-1].strip() if values else ""
        if original and not original.startswith("/work/"):
            raise SystemExit(f"unresolved existing hook {key}: {original}; destination retained")
        hook = "t51_m5_120_" + key.lower() + ".tcl"
        text = f"# Preserve existing {key}, then enable the physical form.\n"
        if original:
            text += f"source {{{original}}}\n"
        text += "source /work/t51_m5_120_profile.tcl\n"
        (dst / hook).write_text(text)
        additions.append(f"override export {key} = /work/{hook}")
    (dst / "config.mk").write_text(config + "\n".join(additions) + "\n")
    manifest = {
        "source": str(src), "destination": str(dst),
        "class": "DRIVE_AND_WIRE", "rtl_pin_cycles_added": 0,
        "changes": ["all signal routing M5-M6 (not per-net)",
                    "repair_design requested max_wire_length 120um; verify placed lengths"],
        "source_config_sha256": hashlib.sha256(config.encode()).hexdigest(),
        "synth_checkpoints": copied,
        "review_gates": ["PLACE image/wire structure", "M5/M6 capacity and pin access before GRT",
                         "GRT density/congestion/clock", "routed signoff and equivalent LEC"],
    }
    (dst / "T51_PHYSICAL_FORM.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
