#!/usr/bin/env python3
"""W18: balanced-clock check of a hierarchical block or die (root 2026-10-01: the parent clock tree honours the
hardened macros' insertion latency from their ETMs; W10b's tiles time their I/O against a balanced tree).

For a routed ORFS result with hard macros that carry an extracted timing model (write_timing_model: the clock
pin's max_clock_tree_path arc is the macro's internal insertion), reports at SS and FF:
  * each macro's clock-pin arrival, its ETM insertion, and their sum (the macro's internal sink arrival);
  * the parent's register clock arrivals (min / median / max);
  * the skew of every macro's internal sinks against the parent registers, against --tolerance-ps.

    python3 tools/w18/clock_balance.py --orfs-dir D --macro physical/w18/<view> [--macro ...] --output R.json

The CTS side of the method is ORFS's CTS with macro clustering of 1 (each macro clock pin its own driver, so
the ETM is read at a sharp slew) and TritonCTS's insertion-delay balancing (on by default; it reads the ETM's
max_clock_tree_path): run_abi3_physical --orfs-var 'CTS_ARGS=-sink_clustering_enable -repair_clock_nets
-macro_clustering_size 1 -macro_clustering_max_diameter 20'.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
CTS_ARGS = "-sink_clustering_enable -repair_clock_nets -macro_clustering_size 1 -macro_clustering_max_diameter 20"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def etm_insertion(lib: Path) -> dict:
    """The clock pin's max/min_clock_tree_path values (ps, rise/fall mean) of an ETM."""
    t = lib.read_text()
    out = {}
    for kind in ("max_clock_tree_path", "min_clock_tree_path"):
        m = re.search(r"timing_type : %s;\s*cell_rise\(scalar\) \{\s*values\(\"([-0-9.]+)\"\);\s*\}\s*cell_fall\(scalar\) "
                      r"\{\s*values\(\"([-0-9.]+)\"\);" % kind, t)
        if m:
            out[kind] = round((float(m.group(1)) + float(m.group(2))) / 2, 1)
    return out


def tcl(corner: str, base: str, macros: list[str]) -> str:
    libs = sorted(f"{PLAT}/lib/NLDM/{x}" for x in [
        "asap7sc7p5t_AO_RVT_{C}_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz",
        "asap7sc7p5t_OA_RVT_{C}_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib",
        "asap7sc7p5t_SIMPLE_RVT_{C}_nldm_211120.lib.gz"])
    libs = [l.replace("{C}", corner.upper()) for l in libs]
    return "\n".join([f"read_lef {PLAT}/lef/asap7_tech_1x_201209.lef", f"read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef",
                      *[f"read_lef /src/{m}/{Path(m).name}.lef" for m in macros], *[f"read_liberty {l}" for l in libs],
                      *[f"read_liberty /src/{m}/{Path(m).name}_{corner}.lib" for m in macros],
                      f"read_db {base}/6_final.odb", f"read_sdc {base}/6_final.sdc", f"read_spef {base}/6_final.spef",
                      "set_propagated_clock [all_clocks]",
                      "foreach p [all_registers -clock_pins] { set a [get_property $p arrival_max_rise]; "
                      "set i [get_cells -of_objects $p]; puts \"OT_CK [get_property $i ref_name] [get_full_name $p] $a\" }",
                      "exit"])


def run(orfs: Path, corner: str, macros: list[str]) -> list[tuple[str, str, float]]:
    base = next((orfs / "results/asap7").glob("*/base"))
    (orfs / f"w18_ckbal_{corner}.tcl").write_text(tcl(corner, f"/work/{base.relative_to(orfs)}", macros))
    out = subprocess.run(["docker", "run", "--rm", "-v", f"{orfs}:/work", "-v", f"{ROOT}:/src:ro", "openroad/orfs:latest",
                          "bash", "-lc", f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "
                                         f"/work/w18_ckbal_{corner}.tcl"], capture_output=True, text=True).stdout
    rows = []
    for ln in out.splitlines():
        p = ln.split()
        if p[:1] == ["OT_CK"] and len(p) >= 4:
            try:
                rows.append((p[1], p[2], float(p[3])))
            except ValueError:
                pass
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--macro", action="append", default=[])
    ap.add_argument("--tolerance-ps", type=float, default=100.0)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    names = {Path(m).name: m for m in a.macro}
    rec = dict(schema="opentallas.v41.w18_clock_balance.v1", orfs_dir=str(a.orfs_dir.resolve()), cts_args=CTS_ARGS,
               tolerance_ps=a.tolerance_ps, corners={})
    for corner in ("ss", "ff"):
        rows = run(a.orfs_dir.resolve(), corner, a.macro)
        scale = 1e12 if rows and max(abs(r[2]) for r in rows) < 1e-6 else 1.0
        regs = [r[2] * scale for r in rows if r[0] not in names]
        mac = []
        for ref_, pin, arr in rows:
            if ref_ in names:
                ins = etm_insertion(ROOT / names[ref_] / f"{ref_}_{corner}.lib")
                mac.append(dict(pin=pin, arrival_ps=round(arr * scale, 1), etm_insertion_ps=ins,
                                internal_sink_ps=round(arr * scale + ins.get("max_clock_tree_path", 0.0), 1)))
        med = statistics.median(regs) if regs else None
        for m in mac:
            m["skew_vs_parent_median_ps"] = round(m["internal_sink_ps"] - med, 1) if med is not None else None
        worst = max((abs(m["skew_vs_parent_median_ps"]) for m in mac if m["skew_vs_parent_median_ps"] is not None), default=None)
        rec["corners"][corner] = dict(parent_registers=len(regs),
                                      parent_arrival_ps=dict(min=round(min(regs), 1), median=round(med, 1), max=round(max(regs), 1)) if regs else None,
                                      macros=mac, worst_macro_skew_ps=worst,
                                      balanced=worst is not None and worst <= a.tolerance_ps)
    rec["macro_views"] = {k: dict(lef_sha256=sha(ROOT / v / f"{k}.lef")) for k, v in names.items()}
    rec["tool_sha256"] = sha(Path(__file__))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({c: dict(parent=v["parent_arrival_ps"], worst=v["worst_macro_skew_ps"], balanced=v["balanced"])
                      for c, v in rec["corners"].items()}, indent=1))


if __name__ == "__main__":
    main()
