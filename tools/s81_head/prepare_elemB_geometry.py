#!/usr/bin/env python3
"""Re-place the R6 elemB synthesis with reviewed R7 pins and measured density.

No RTL, clock or latency change. The old kit remains untouched. Copy the original
synthesis and floorplan checkpoints, without any stale placement checkpoints.
"""
import argparse
import json
import re
import shutil
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("pins", type=Path)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit("Refusing an existing output directory")
    # GPL's actual movable utilization, including the pin-density area adjust.
    log = (a.source / "run/logs/asap7/hd_elemB_rb/base/3_3_place_gp.log").read_text()
    util = float(re.search(r"Utilization:\s+([\d.]+) %", log)[1]) / 100
    density = round(util + 0.04, 2)
    if not 0 < util < density < 0.6:
        raise SystemExit("Invalid measured density")
    a.out.mkdir(parents=True)
    for f in a.source.iterdir():
        if f.name in {"run", "trial.log", "image.txt", "__pycache__", ".ot-run-spill-copy"}:
            continue
        if f.is_dir():
            shutil.copytree(f, a.out / f.name)
        else:
            shutil.copy2(f, a.out / f.name)
    r = Path("run/results/asap7/hd_elemB_rb/base")
    (a.out / r).mkdir(parents=True)
    for f in (a.source / r).iterdir():
        if f.name.startswith("1_") or f.name in {"mem.json", "2_floorplan.odb", "2_floorplan.sdc"}:
            shutil.copy2(f, a.out / r / f.name)
    pp = json.loads(a.pins.read_text())["pins"]
    baseline = json.loads((a.source / "pins.json").read_text())
    byname = {p["name"]: p for p in pp}
    for p in baseline:
        name = p["bus"] + (f'[{p["bit"]}]' if p.get("bit") is not None else "")
        q = byname[name]
        p.update(x=q["x"], y=q["y"], layer=q["layer"])
        p["face"] = min((p["x"], "W"), (285.12-p["x"], "E"),
                        (p["y"], "S"), (285.12-p["y"], "N"))[1]
    (a.out / "pins.json").write_text(json.dumps(baseline, indent=1) + "\n")
    # Infrastructure ports retain their centre-island contract from the R6 kit.
    infra = {"clk", "rst_n"}
    lines = []
    for p in pp:
        if p["name"] in infra or p["name"].startswith("ft_"):
            continue
        w, h = (0.084, 0.024) if p["layer"] == "M4" else (0.024, 0.084)
        lines.append(f'place_pin -pin_name {{{p["name"]}}} -layer {p["layer"]} '
                     f'-location {{{p["x"]:.4f} {p["y"]:.4f}}} -pin_size {{{w} {h}}}')
    lines.append("source /work/island_elemB_pins.tcl")
    (a.out / "io.tcl").write_text("\n".join(lines) + "\n")
    cfg = (a.out / "config.mk").read_text()
    cfg, count = re.subn(r"export PLACE_DENSITY = [^\n]+", f"export PLACE_DENSITY = {density}", cfg)
    assert count == 1
    (a.out / "config.mk").write_text(cfg)
    (a.out / "geometry_delta.json").write_text(json.dumps(dict(
        source=str(a.source), pins=str(a.pins), measured_utilization=util,
        placement_density=density, cycles_added=0, rtl_changed=False,
        scope="Placement-only geometry trial; no CTS, route, STA or sign-off"), indent=2)+"\n")
    print(a.out, "density", density, "util", util, "signal pins", len(baseline))


if __name__ == "__main__":
    main()
